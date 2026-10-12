"""
Generador de carga concurrente para Cheapest (NestJS) vía API Gateway.

Ejemplo para Operación normal:
    python load_test.py --users 900 --ramp-up 5 --duration 50 --rate 8.333 --get-percent 70

La tasa (--rate) es la tasa TOTAL objetivo en solicitudes/segundo.
El porcentaje reparte esa tasa entre GET y POST.
--users limita la concurrencia máxima; no significa por sí solo que se
generen 900 solicitudes por segundo ni 900 usuarios que envían continuamente.

Requiere:
    pip install httpx
"""

import argparse
import asyncio
import csv
import json
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


# ============================================================
# CONFIGURACIÓN DEL DESPLIEGUE
# ============================================================

BASE_URL = "https://o2mke4696e.execute-api.us-east-1.amazonaws.com/lab"

TIENDA_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ZONA = "Zona Norte"
MONEDA_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

PRODUCTOS = [
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaab",
]


def build_post_body():
    """Genera un pedido con 25 ítems y un identificador único."""
    items = []
    for i in range(25):
        producto_id = PRODUCTOS[i % len(PRODUCTOS)]
        items.append({
            "productoId": producto_id,
            "cantidad": random.randint(1, 10),
            "precioUnitario": round(random.uniform(1000, 20000), 2),
            "descuento": 0,
            "monedaId": MONEDA_ID,
        })

    monto_total = sum(
        item["precioUnitario"] * item["cantidad"] - item["descuento"]
        for item in items
    )

    now = datetime.now(timezone.utc)
    return {
        "identificador": (
            f"PED-LOADTEST-{now.strftime('%Y%m%dT%H%M%S%f')}-"
            f"{random.randint(0, 999999)}"
        ),
        "tiendaId": TIENDA_ID,
        "fechaHoraCreacion": now.isoformat(),
        "montoTotal": round(monto_total, 2),
        "monedaId": MONEDA_ID,
        "estado": "creado",
        "items": items,
    }


def get_endpoint():
    return (
        "/logistics/tenderos/productos-disponibles"
        f"?tiendaId={TIENDA_ID}&zona={ZONA.replace(' ', '%20')}"
    )


POST_ENDPOINT = "/logistics/pedidos"


async def send_request(client, method, endpoint, body, run_id):
    start = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    status_code = None
    error = ""

    try:
        if method == "GET":
            response = await client.get(BASE_URL + endpoint)
        else:
            response = await client.post(BASE_URL + endpoint, json=body)

        status_code = response.status_code
        if status_code >= 400:
            error = f"HTTP {status_code}"
    except httpx.TimeoutException:
        error = "timeout"
    except httpx.ConnectError:
        error = "connection_error"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    latency_ms = (time.perf_counter() - start) * 1000
    return {
        "run_id": run_id,
        "timestamp_iso": timestamp,
        "endpoint_type": method,
        "method": method,
        "url": BASE_URL + endpoint,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }


async def request_producer(
    client,
    method,
    endpoint,
    rate,
    ramp_up,
    duration,
    semaphore,
    results,
    run_id,
    start_time,
    body_factory=None,
):
    """
    Genera solicitudes a una tasa objetivo para este endpoint.
    GET y POST tienen productores independientes y arrancan juntos.
    """
    if rate <= 0:
        return

    deadline = start_time + ramp_up + duration
    request_number = 0

    while True:
        now = time.perf_counter()
        elapsed = now - start_time
        if now >= deadline:
            break

        # Durante el ramp-up aumenta gradualmente desde el 25 % hasta el 100 %.
        if ramp_up > 0 and elapsed < ramp_up:
            progress = max(0.0, elapsed / ramp_up)
            current_rate = rate * (0.25 + 0.75 * progress)
        else:
            current_rate = rate

        target_time = start_time + request_number / max(current_rate, 0.001)
        now = time.perf_counter()
        if target_time > now:
            await asyncio.sleep(target_time - now)

        if time.perf_counter() >= deadline:
            break

        body = body_factory() if body_factory else None

        async def execute_one(payload=body):
            async with semaphore:
                return await send_request(
                    client, method, endpoint, payload, run_id
                )

        task = asyncio.create_task(execute_one())
        # Recoger cada tarea al terminar para no acumular miles de tareas.
        task.add_done_callback(lambda completed: results.append(completed.result()))
        request_number += 1

        # Evita una espera ocupada cuando la tasa solicitada es alta.
        await asyncio.sleep(0)


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    position = (len(values) - 1) * p / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def summarize(method, results, measurement_seconds):
    total = len(results)
    errors = [
        item for item in results
        if item["error"] or item["status_code"] is None or item["status_code"] >= 400
    ]
    successful = [
        item for item in results
        if not item["error"] and item["status_code"] is not None and item["status_code"] < 400
    ]
    latencies = [item["latency_ms"] for item in successful]
    error_pct = (len(errors) / total * 100) if total else 0.0
    throughput = total / measurement_seconds if measurement_seconds > 0 else 0.0

    summary = {
        "endpoint_type": method,
        "total_requests": total,
        "successful_requests": len(successful),
        "errors": len(errors),
        "error_pct": round(error_pct, 2),
        "throughput_req_s": round(throughput, 3),
        "avg_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2),
    }

    print(f"\n===== RESUMEN {method} =====")
    print(f"Solicitudes:       {summary['total_requests']}")
    print(f"Exitosas:          {summary['successful_requests']}")
    print(f"Errores:           {summary['errors']} ({summary['error_pct']:.2f}%)")
    print(f"Throughput:        {summary['throughput_req_s']:.3f} req/s")
    print(f"Latencia promedio: {summary['avg_ms']:.2f} ms")
    print(f"p95:               {summary['p95_ms']:.2f} ms")
    print(f"p99:               {summary['p99_ms']:.2f} ms")
    return summary


def export_csv(run_id, results, summaries, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Trazabilidad individual de cada petición, separada por endpoint.
    for method, suffix in (("GET", "get"), ("POST", "post")):
        filename = output_dir / f"{run_id}_results_{suffix}.csv"
        fields = [
            "run_id", "timestamp_iso", "endpoint_type", "method", "url",
            "status_code", "latency_ms", "error",
        ]
        with filename.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(item for item in results if item["endpoint_type"] == method)
        print(f"CSV de solicitudes: {filename}")

    summary_file = output_dir / f"{run_id}_summary.csv"
    fields = [
        "run_id", "generated_at_utc", "duration_s", "total_users",
        "get_percent", "post_percent", "target_rate_total_req_s",
        "endpoint_type", "total_requests", "successful_requests", "errors",
        "error_pct", "throughput_req_s", "avg_ms", "p95_ms", "p99_ms",
    ]
    with summary_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for item in summaries:
            writer.writerow({**item["metadata"], **item["summary"]})
    print(f"CSV de resumen: {summary_file}")


async def run_test(args):
    if args.users < 1:
        raise ValueError("--users debe ser al menos 1.")
    if args.duration < 1:
        raise ValueError("--duration debe ser al menos 1 segundo.")
    if args.ramp_up < 0:
        raise ValueError("--ramp-up no puede ser negativo.")
    if not 0 <= args.get_percent <= 100:
        raise ValueError("--get-percent debe estar entre 0 y 100.")
    if args.rate <= 0:
        raise ValueError("--rate debe ser mayor que cero.")

    get_rate = args.rate * args.get_percent / 100
    post_rate = args.rate * (100 - args.get_percent) / 100
    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    started_at = datetime.now(timezone.utc).isoformat()

    print("=" * 68)
    print("CHEAPEST — PRUEBA CONCURRENTE GET + POST")
    print(f"Run ID:                 {run_id}")
    print(f"API Gateway:            {BASE_URL}")
    print(f"Usuarios/capacidad max: {args.users}")
    print(f"Duración medida:        {args.duration} s")
    print(f"Ramp-up:                {args.ramp_up} s")
    print(f"Distribución GET/POST:  {args.get_percent}/{100 - args.get_percent}")
    print(f"Tasa total objetivo:    {args.rate:.3f} req/s")
    print(f"Tasa GET objetivo:      {get_rate:.3f} req/s")
    print(f"Tasa POST objetivo:     {post_rate:.3f} req/s")
    print("=" * 68)

    limits = httpx.Limits(
        max_connections=args.users,
        max_keepalive_connections=min(args.users, 100),
    )
    timeout = httpx.Timeout(args.timeout)
    semaphore = asyncio.Semaphore(args.users)
    results = []

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        headers={"User-Agent": "Cheapest-LoadTest/1.0"},
    ) as client:
        start_time = time.perf_counter()
        producers = [
            asyncio.create_task(
                request_producer(
                    client, "GET", get_endpoint(), get_rate,
                    args.ramp_up, args.duration, semaphore, results,
                    run_id, start_time,
                )
            ),
            asyncio.create_task(
                request_producer(
                    client, "POST", POST_ENDPOINT, post_rate,
                    args.ramp_up, args.duration, semaphore, results,
                    run_id, start_time, build_post_body,
                )
            ),
        ]
        await asyncio.gather(*producers)

        # Espera las solicitudes que ya se lanzaron antes de cerrar el cliente.
        # El tiempo máximo de espera se limita por el timeout HTTP configurado.
        await asyncio.sleep(args.timeout + 0.1)

    measurement_seconds = args.duration + args.ramp_up
    summaries = []
    metadata = {
        "run_id": run_id,
        "generated_at_utc": started_at,
        "duration_s": args.duration,
        "total_users": args.users,
        "get_percent": args.get_percent,
        "post_percent": 100 - args.get_percent,
        "target_rate_total_req_s": args.rate,
    }
    for method in ("GET", "POST"):
        summary = summarize(
            method,
            [item for item in results if item["endpoint_type"] == method],
            measurement_seconds,
        )
        summaries.append({"metadata": metadata, "summary": summary})

    export_csv(run_id, results, summaries, args.output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta GET y POST simultáneamente contra Cheapest API Gateway."
    )
    parser.add_argument("--users", type=int, required=True,
                        help="Límite de concurrencia total (no equivale a req/s).")
    parser.add_argument("--ramp-up", type=int, default=5,
                        help="Duración del ramp-up en segundos.")
    parser.add_argument("--duration", type=int, default=50,
                        help="Duración objetivo de la prueba en segundos.")
    parser.add_argument("--rate", type=float, required=True,
                        help="Tasa TOTAL objetivo de GET+POST en solicitudes/segundo.")
    parser.add_argument("--get-percent", type=float, default=70,
                        help="Porcentaje GET; el restante corresponde a POST (default 70).")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="Timeout por petición en segundos.")
    parser.add_argument("--output-dir", default="load_test_results",
                        help="Directorio para los CSV.")
    args = parser.parse_args()
    asyncio.run(run_test(args))


if __name__ == "__main__":
    main()
