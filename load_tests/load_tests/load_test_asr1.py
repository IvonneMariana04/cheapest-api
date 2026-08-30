import requests
import time
import statistics
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "http://localhost:3000/logistics/productos/disponibles-tendero"

PARAMS = {
    "tiendaId": "84db11a3-6393-49e8-aa8b-aa1ccc0fafd9",
    "zona": "Zona Centro"
}


def request():
    inicio = time.perf_counter()

    try:
        response = requests.get(
            URL,
            params=PARAMS,
            timeout=30
        )

        tiempo = (time.perf_counter() - inicio) * 1000

        return {
            "tiempo": tiempo,
            "status": response.status_code,
            "ok": response.status_code == 200
        }

    except Exception:
        tiempo = (time.perf_counter() - inicio) * 1000

        return {
            "tiempo": tiempo,
            "status": 0,
            "ok": False
        }


def percentile(data, p):
    data = sorted(data)

    if not data:
        return 0

    index = int(len(data) * p / 100)

    if index >= len(data):
        index = len(data) - 1

    return data[index]


def prueba(usuarios, ramp_up, duration=None):

    print("\n" + "=" * 70)
    print(
        f"PRUEBA: {usuarios} usuarios | "
        f"Ramp-up: {ramp_up}s | "
        f"Duración: {duration if duration else 'N/A'}"
    )
    print("=" * 70)

    resultados = []

    inicio_total = time.perf_counter()

    # ---------------------------------------------------------
    # SIN DURACIÓN:
    # cada usuario hace una petición.
    # Se utiliza para Smoke, Baja, Media y Normal.
    # ---------------------------------------------------------

    if duration is None:

        intervalo = ramp_up / usuarios

        with ThreadPoolExecutor(max_workers=usuarios) as executor:

            futures = []

            for _ in range(usuarios):

                futures.append(
                    executor.submit(request)
                )

                time.sleep(intervalo)

            for future in as_completed(futures):
                resultados.append(future.result())

    # ---------------------------------------------------------
    # CON DURACIÓN:
    # se crean usuarios progresivamente durante el ramp-up.
    # Después se mantiene la carga durante "duration" segundos.
    # ---------------------------------------------------------

    else:

        with ThreadPoolExecutor(max_workers=usuarios) as executor:

            futures = []

            intervalo = ramp_up / usuarios

            inicio_ramp_up = time.perf_counter()

            for _ in range(usuarios):

                futures.append(
                    executor.submit(request)
                )

                time.sleep(intervalo)

            # Esperamos hasta completar la duración solicitada
            transcurrido = time.perf_counter() - inicio_ramp_up

            restante = duration - transcurrido

            if restante > 0:
                time.sleep(restante)

            for future in as_completed(futures):
                resultados.append(future.result())

    duracion_real = time.perf_counter() - inicio_total

    tiempos = [
        r["tiempo"]
        for r in resultados
    ]

    exitosas = sum(
        r["ok"]
        for r in resultados
    )

    errores = len(resultados) - exitosas

    error_pct = (
        errores / len(resultados) * 100
        if resultados
        else 0
    )

    throughput = (
        len(resultados) / duracion_real
        if duracion_real > 0
        else 0
    )

    print("\nResultados:")
    print(f"Requests:      {len(resultados)}")
    print(f"Exitosas:      {exitosas}")
    print(f"Errores:       {errores}")
    print(f"Error %:       {error_pct:.2f}%")
    print(f"Duración:      {duracion_real:.2f} s")
    print(f"Throughput:    {throughput:.2f} req/s")

    if tiempos:

        p95 = percentile(tiempos, 95)
        p99 = percentile(tiempos, 99)

        print(f"Promedio:      {statistics.mean(tiempos):.2f} ms")
        print(f"P95:           {p95:.2f} ms")
        print(f"P99:           {p99:.2f} ms")
        print(f"Mínimo:        {min(tiempos):.2f} ms")
        print(f"Máximo:        {max(tiempos):.2f} ms")

        if p99 < 1000:
            print("ASR1: CUMPLE ✓")
        else:
            print("ASR1: NO CUMPLE ✗")

    return {
        "usuarios": usuarios,
        "ramp_up": ramp_up,
        "duracion": duracion_real,
        "requests": len(resultados),
        "errores": errores,
        "error_pct": error_pct,
        "throughput": throughput,
        "p95": percentile(tiempos, 95),
        "p99": percentile(tiempos, 99)
    }


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

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
        default=None
    )

    args = parser.parse_args()

    prueba(
        args.users,
        args.ramp_up,
        args.duration
    )