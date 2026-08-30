import requests
import time
import statistics
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
            "respuesta": response.text,
            "ok": response.status_code == 200
        }

    except Exception as e:
        tiempo = (time.perf_counter() - inicio) * 1000

        return {
            "tiempo": tiempo,
            "status": 0,
            "respuesta": str(e),
            "ok": False
        }


def percentile(data, p):
    data = sorted(data)

    index = int(len(data) * p / 100)

    if index >= len(data):
        index = len(data) - 1

    return data[index]


def prueba(usuarios, ramp_up):

    print("\n" + "=" * 60)
    print(f"PRUEBA: {usuarios} usuarios | Ramp-up: {ramp_up}s")
    print("=" * 60)

    resultados = []

    intervalo = ramp_up / usuarios

    inicio_total = time.perf_counter()

    with ThreadPoolExecutor(max_workers=usuarios) as executor:

        futures = []

        for _ in range(usuarios):

            futures.append(
                executor.submit(request)
            )

            time.sleep(intervalo)

        for future in as_completed(futures):
            resultados.append(
                future.result()
            )
            
        print("\nResultados individuales:")
            
        for i, r in enumerate(resultados, 1):
            print(
                f"Request {i}: "
                f"status={r['status']} | "
                f"tiempo={r['tiempo']:.2f} ms | "
                f"ok={r['ok']}"
            )

            if not r["ok"]:
                print(f"  Respuesta: {r['respuesta']}")

    duracion = time.perf_counter() - inicio_total

    tiempos = [
        r["tiempo"]
        for r in resultados
    ]

    exitosas = sum(
        r["ok"]
        for r in resultados
    )

    errores = len(resultados) - exitosas

    print(f"Requests:      {len(resultados)}")
    print(f"Exitosas:      {exitosas}")
    print(f"Errores:       {errores}")
    print(f"Duración:      {duracion:.2f} s")
    print(f"Promedio:      {statistics.mean(tiempos):.2f} ms")
    print(f"P95:           {percentile(tiempos, 95):.2f} ms")
    print(f"P99:           {percentile(tiempos, 99):.2f} ms")
    print(f"Mínimo:        {min(tiempos):.2f} ms")
    print(f"Máximo:        {max(tiempos):.2f} ms")

    p99 = percentile(tiempos, 99)

    if p99 < 1000:
        print("ASR1: CUMPLE ✓")
    else:
        print("ASR1: NO CUMPLE ✗")


if __name__ == "__main__":

    prueba(5, 5)