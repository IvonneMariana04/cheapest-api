"""
Load testing script for Cheapest backend (NestJS)

Examples:

GET:
python load_test.py --endpoint GET --users 1500 --ramp-up 75 --duration 60

POST:
python load_test.py --endpoint POST --users 1500 --ramp-up 75 --duration 60

POST con body externo:
python load_test.py --endpoint POST --users 1500 --ramp-up 75 --duration 60 --body sample_body.json

Requires:
    pip install httpx
"""

import asyncio
import argparse
import csv
import json
import random
import statistics
import time
from datetime import datetime, timezone

import httpx


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_URL = "http://localhost:3000"

TIENDA_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ZONA = "Zona Norte"
MONEDA_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

PRODUCTOS = [
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaab",
]


# ============================================================
# BODY POST
# ============================================================

def build_post_body():
    """
    Genera un pedido grande con 25 ítems.
    """

    items = []

    for i in range(25):

        producto_id = PRODUCTOS[i % len(PRODUCTOS)]

        items.append({
            "productoId": producto_id,
            "cantidad": random.randint(1, 10),
            "precioUnitario": round(
                random.uniform(1000, 20000),
                2
            ),
            "descuento": 0,
            "monedaId": MONEDA_ID
        })


    monto_total = sum(
        item["precioUnitario"] * item["cantidad"]
        - item["descuento"]
        for item in items
    )


    return {
        "identificador": (
            f"PED-LOADTEST-"
            f"{int(time.time() * 1000)}-"
            f"{random.randint(0, 999999)}"
        ),

        "tiendaId": TIENDA_ID,

        "fechaHoraCreacion": datetime.now(
            timezone.utc
        ).isoformat(),

        "montoTotal": round(
            monto_total,
            2
        ),

        "monedaId": MONEDA_ID,

        "estado": "creado",

        "items": items
    }


# ============================================================
# PETICIÓN HTTP
# ============================================================

async def send_request(
    client,
    method,
    endpoint,
    body=None
):

    start = time.perf_counter()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    status_code = None
    error = ""


    try:

        if method == "GET":

            response = await client.get(
                BASE_URL + endpoint
            )

        else:

            response = await client.post(
                BASE_URL + endpoint,
                json=body
            )


        status_code = response.status_code


        if status_code >= 400:

            error = f"HTTP {status_code}"


    except httpx.TimeoutException:

        error = "timeout"


    except httpx.ConnectError:

        error = "connection_error"


    except Exception as e:

        error = str(e)


    latency_ms = (
        time.perf_counter() - start
    ) * 1000


    return {
        "timestamp_iso": timestamp,
        "status_code": status_code,
        "latency_ms": round(
            latency_ms,
            2
        ),
        "error": error
    }


# ============================================================
# WORKER
# ============================================================

async def worker(
    client,
    method,
    endpoint,
    body_fn,
    stop_time,
    results
):

    while time.perf_counter() < stop_time:

        body = (
            body_fn()
            if body_fn
            else None
        )


        result = await send_request(
            client,
            method,
            endpoint,
            body
        )


        results.append(result)


# ============================================================
# EJECUTAR PRUEBA
# ============================================================

async def run_load_test(
    endpoint,
    users,
    ramp_up,
    duration,
    custom_body=None
):

    if endpoint == "GET":

        method = "GET"

        api_endpoint = (
            "/logistics/tenderos/"
            "productos-disponibles"
            f"?tiendaId={TIENDA_ID}"
            f"&zona={ZONA.replace(' ', '%20')}"
        )

        body_fn = None


    else:

        method = "POST"

        api_endpoint = (
            "/logistics/pedidos"
        )


        if custom_body is not None:

            def body_fn():
                return custom_body.copy()

        else:

            body_fn = build_post_body


    print()
    print("=" * 60)
    print(f"PRUEBA {endpoint}")
    print("=" * 60)
    print(f"Usuarios:       {users}")
    print(f"Ramp-up:        {ramp_up} segundos")
    print(f"Duración:       {duration} segundos")
    print(f"Endpoint:       {api_endpoint}")
    print("=" * 60)
    print()


    results = []


    limits = httpx.Limits(
        max_connections=users,
        max_keepalive_connections=users
    )


    timeout = httpx.Timeout(
        15.0
    )


    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout
    ) as client:


        start_time = time.perf_counter()


        stop_time = (
            start_time
            + ramp_up
            + duration
        )


        tasks = []


        # Incorporación progresiva
        # de los usuarios.
        delay_between_users = (
            ramp_up / users
            if users > 0
            else 0
        )


        for i in range(users):

            delay = (
                delay_between_users * i
            )


            async def delayed_worker(
                delay=delay
            ):

                await asyncio.sleep(
                    delay
                )


                await worker(
                    client,
                    method,
                    api_endpoint,
                    body_fn,
                    stop_time,
                    results
                )


            tasks.append(
                asyncio.create_task(
                    delayed_worker()
                )
            )


        await asyncio.gather(
            *tasks
        )


    return results


# ============================================================
# PERCENTILES
# ============================================================

def percentile(
    data,
    p
):

    if not data:
        return 0


    data = sorted(data)


    k = (
        len(data) - 1
    ) * (
        p / 100
    )


    f = int(k)


    c = min(
        f + 1,
        len(data) - 1
    )


    if f == c:

        return data[f]


    return (
        data[f]
        + (
            data[c]
            - data[f]
        ) * (
            k - f
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def print_summary(
    endpoint,
    results,
    total_duration
):

    latencies = [
        r["latency_ms"]
        for r in results
        if (
            r["error"] == ""
            and r["status_code"] is not None
            and r["status_code"] < 400
        )
    ]


    errors = [
        r
        for r in results
        if (
            r["error"] != ""
            or r["status_code"] is None
            or r["status_code"] >= 400
        )
    ]


    total = len(results)

    successful = (
        total - len(errors)
    )


    error_pct = (
        len(errors)
        / total
        * 100
        if total
        else 0
    )


    throughput = (
        total
        / total_duration
        if total_duration
        else 0
    )


    print()
    print("=" * 60)
    print(f"RESUMEN — {endpoint}")
    print("=" * 60)

    print(
        f"Total requests:     {total}"
    )

    print(
        f"Requests exitosas:  {successful}"
    )

    print(
        f"Errores:            "
        f"{len(errors)} "
        f"({error_pct:.2f}%)"
    )

    print(
        f"Throughput:         "
        f"{throughput:.2f} req/s"
    )


    if latencies:

        print(
            f"Latencia promedio:  "
            f"{statistics.mean(latencies):.2f} ms"
        )

        print(
            f"Latencia p95:       "
            f"{percentile(latencies, 95):.2f} ms"
        )

        print(
            f"Latencia p99:       "
            f"{percentile(latencies, 99):.2f} ms"
        )

    else:

        print(
            "No hubo latencias válidas."
        )


    print("=" * 60)
    print()


# ============================================================
# CSV
# ============================================================

def export_csv(
    endpoint,
    results
):

    filename = (
        "results_get.csv"
        if endpoint == "GET"
        else "results_post.csv"
    )


    fields = [
        "timestamp_iso",
        "status_code",
        "latency_ms",
        "error"
    ]


    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )


        writer.writeheader()

        writer.writerows(
            results
        )


    print(
        f"Resultados exportados a {filename}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--endpoint",
        choices=["GET", "POST"],
        required=True
    )


    parser.add_argument(
        "--users",
        type=int,
        required=True
    )


    parser.add_argument(
        "--ramp-up",
        type=int,
        required=True
    )


    parser.add_argument(
        "--duration",
        type=int,
        default=60
    )


    parser.add_argument(
        "--body",
        type=str,
        default=None
    )


    args = parser.parse_args()


    custom_body = None


    if args.body:

        with open(
            args.body,
            "r",
            encoding="utf-8"
        ) as file:

            custom_body = json.load(
                file
            )


    start = time.perf_counter()


    results = asyncio.run(
        run_load_test(
            args.endpoint,
            args.users,
            args.ramp_up,
            args.duration,
            custom_body
        )
    )


    total_duration = (
        time.perf_counter()
        - start
    )


    print_summary(
        args.endpoint,
        results,
        total_duration
    )


    export_csv(
        args.endpoint,
        results
    )


if __name__ == "__main__":
    main()