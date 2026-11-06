# Calibración del mecanismo de ojos

PCA9685 en I2C 0x40. Pulsos 600–2400 µs (0–180°), 50 Hz. Fuente V+ 5 V.

| Canal | Parte                     | Centro | Abierto | Cerrado | Sentido para abrir |
|-------|---------------------------|--------|---------|---------|--------------------|
| 0     | Párpado inferior derecho  | 90     | 45      | 138     | bajar ángulo       |
| 1     | Párpado superior derecho  | 90     | 150     | 42      | subir ángulo       |
| 2     | Ojos arriba/abajo         | 100    | abajo 0 | arriba 180 | bajar = abajo. Abajo: párp. sup. ≤90. Arriba: párp. inf. a 110/70 |
| 3     | Párpado inferior izquierdo| 90     | 140     | 30      | subir ángulo       |
| 4     | Párpado superior izquierdo| 90     | 15      | 135     | bajar ángulo       |
| 5     | Ojos izquierda/derecha    | 90     | der. 40 | izq. 130| bajar = su derecha |
