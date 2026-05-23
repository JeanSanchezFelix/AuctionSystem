#!/bin/bash

SERVER_SCRIPT="server_main.py"
CLIENT_SCRIPT="client_main.py"

SERVER_LOG="server.log"
CLIENT1_LOG="client1.log"
CLIENT2_LOG="client2.log"
CLIENT3_LOG="client3.log"

rm -f "$SERVER_LOG" "$CLIENT1_LOG" "$CLIENT2_LOG" "$CLIENT3_LOG"

TOTAL_SCORE=0

echo "=== Grupo 1: creacion y manejo de hilos ==="

echo "Test 1: verificar uso de threading"
if grep -q "import threading" server_functions.py && \
   grep -q "import threading" client_functions.py; then
    echo "[OK] Uso de threading detectado"
    TOTAL_SCORE=$((TOTAL_SCORE + 10))
else
    echo "[FAIL] No se detecto uso de threading"
fi

echo
echo "=== Grupo 2: verificacion de sockets ==="

echo "Test 2: verificar uso de socket"
if grep -q "import socket" server_functions.py && \
   grep -q "import socket" client_functions.py; then
    echo "[OK] Uso de socket detectado"
    TOTAL_SCORE=$((TOTAL_SCORE + 10))
else
    echo "[FAIL] No se detecto uso de socket"
fi

echo
echo "Test 3: lanzar servidor"
AUCTION_DURATION=4 EXPECTED_CLIENTS=3 python3 "$SERVER_SCRIPT" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
sleep 1

if ps -p $SERVER_PID > /dev/null; then
    echo "[OK] Servidor lanzado con PID $SERVER_PID"
    TOTAL_SCORE=$((TOTAL_SCORE + 10))
else
    echo "[FAIL] El servidor no inicio"
    echo "TOTAL_SCORE: $TOTAL_SCORE"
    exit 1
fi

echo
echo "Test 4: lanzar clientes y simular subastas"

(
  {
    echo "Alice"
    sleep 1
    echo "VIEW"
    sleep 1
    echo "BID 550"
    sleep 1
    echo "BID 560"
    sleep 7
    echo "PASS"
  } | python3 "$CLIENT_SCRIPT"
) > "$CLIENT1_LOG" 2>&1 &
C1_PID=$!

(
  {
    echo "Bob"
    sleep 2
    echo "VIEW"
    sleep 1
    echo "BID 600"
    sleep 1
    echo "BID 620"
    sleep 5
    echo "PASS"
  } | python3 "$CLIENT_SCRIPT"
) > "$CLIENT2_LOG" 2>&1 &
C2_PID=$!

(
  {
    echo "Carol"
    sleep 8
    echo "VIEW"
    sleep 1
    echo "BID 650"
    sleep 1
    echo "BID 660"
    sleep 5
    echo "BID 550"
  } | python3 "$CLIENT_SCRIPT"
) > "$CLIENT3_LOG" 2>&1 &
C3_PID=$!

wait $C1_PID
wait $C2_PID
wait $C3_PID
wait $SERVER_PID

echo "[INFO] Todos los procesos principales terminaron"

echo
echo "Test 5: verificar subastas y aceptacion de clientes"
AUCTIONS=$(grep -c "AUCTION_START ITEM=" "$SERVER_LOG")
if [ "$AUCTIONS" -eq 3 ]; then
    echo "[OK] Se detectaron 3 subastas"
    TOTAL_SCORE=$((TOTAL_SCORE + 10))
else
    echo "[FAIL] Se esperaban 3 subastas y se encontraron $AUCTIONS"
fi

echo
echo "=== Grupo 3: bids y logica de subasta ==="

echo "Test 6: verificar ganadores por item"
ITEM_SCORE=0

if grep -q "AUCTION_END ITEM=Laptop WINNER=Bob PRICE=600" "$SERVER_LOG"; then
    echo "[OK] Laptop adjudicada a Bob"
    ITEM_SCORE=$((ITEM_SCORE + 5))
else
    echo "[FAIL] Laptop no tuvo el ganador esperado"
fi

if grep -q "AUCTION_END ITEM=Phone WINNER=Carol PRICE=650" "$SERVER_LOG"; then
    echo "[OK] Phone adjudicado a Carol"
    ITEM_SCORE=$((ITEM_SCORE + 5))
else
    echo "[FAIL] Phone no tuvo el ganador esperado"
fi

if grep -q "AUCTION_END ITEM=Tablet WINNER=Carol PRICE=550" "$SERVER_LOG"; then
    echo "[OK] Tablet adjudicada a Carol"
    ITEM_SCORE=$((ITEM_SCORE + 5))
else
    echo "[FAIL] Tablet no tuvo el ganador esperado"
fi

TOTAL_SCORE=$((TOTAL_SCORE + ITEM_SCORE))

echo
echo "Test 7: verificar rechazo de ofertas invalidas"
LOW_BIDS=$(grep -h "ERROR BID_TOO_LOW" "$CLIENT1_LOG" "$CLIENT2_LOG" "$CLIENT3_LOG" | wc -l)
if [ "$LOW_BIDS" -ge 2 ]; then
    echo "[OK] Se detectaron ofertas invalidas rechazadas"
    TOTAL_SCORE=$((TOTAL_SCORE + 10))
else
    echo "[FAIL] No se detectaron suficientes rechazos de ofertas invalidas"
fi

echo
echo "Test 8: verificar mensajes asincronos en clientes"
ASYNC_OK=0

if grep -q "AUCTION_START ITEM=Laptop" "$CLIENT1_LOG" && \
   grep -q "NEW_BID NAME=Bob PRICE=600" "$CLIENT1_LOG" && \
   grep -q "AUCTION_END ITEM=Laptop WINNER=Bob PRICE=600" "$CLIENT1_LOG"; then
    echo "[OK] Cliente 1 recibio mensajes asincronos"
    ASYNC_OK=$((ASYNC_OK + 4))
else
    echo "[FAIL] Cliente 1 no muestra correctamente los eventos asincronos"
fi

if grep -q "AUCTION_START ITEM=Phone" "$CLIENT2_LOG" && \
   grep -q "AUCTION_END ITEM=Phone WINNER=Carol PRICE=650" "$CLIENT2_LOG"; then
    echo "[OK] Cliente 2 recibio mensajes asincronos"
    ASYNC_OK=$((ASYNC_OK + 3))
else
    echo "[FAIL] Cliente 2 no muestra correctamente los eventos asincronos"
fi

if grep -q "AUCTION_START ITEM=Tablet" "$CLIENT3_LOG" && \
   grep -q "SERVER_SHUTDOWN" "$CLIENT3_LOG"; then
    echo "[OK] Cliente 3 recibio cierre del servidor"
    ASYNC_OK=$((ASYNC_OK + 3))
else
    echo "[FAIL] Cliente 3 no recibio correctamente el cierre"
fi

TOTAL_SCORE=$((TOTAL_SCORE + ASYNC_OK))

echo
echo "Test 9: verificar timer"
TIME_EVENTS=$(grep -c "TIME_LEFT ITEM=" "$SERVER_LOG")
if [ "$TIME_EVENTS" -ge 3 ]; then
    echo "[OK] El temporizador genero eventos TIME_LEFT"
    TOTAL_SCORE=$((TOTAL_SCORE + 5))
else
    echo "[FAIL] No se detectaron suficientes eventos del temporizador"
fi

echo
echo "=== Cierre y limpieza ==="

echo "Test 10: verificar cierre de procesos y sockets"
FAIL_PROC=0
for pid in $SERVER_PID $C1_PID $C2_PID $C3_PID; do
    if ps -p $pid > /dev/null 2>&1; then
        echo "[FAIL] El proceso PID=$pid sigue vivo"
        FAIL_PROC=1
    fi
done

if [ "$FAIL_PROC" -eq 0 ] && grep -q "SERVER_CLOSED" "$SERVER_LOG"; then
    echo "[OK] Cierre correcto de procesos y socket del servidor"
    TOTAL_SCORE=$((TOTAL_SCORE + 20))
else
    echo "[FAIL] No se detecto cierre correcto"
fi

echo
echo "TOTAL_SCORE: $TOTAL_SCORE"