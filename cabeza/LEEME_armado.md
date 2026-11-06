# Montura RobotFace (EyeMech ε3.2 sobre la pantalla)

Mecanismo a la vista, ojos al ras del frente de la pantalla. Base de acrílico de 5 mm (ya
cortada) con piezas chicas impresas que entran en sus ranuras. Caja de MDF solo para la
electrónica.

## laser/
| Archivo | Material |
|---|---|
| base_acrilico5.svg | Acrílico 5 mm (la que ya se cortó) |
| caja_mdf3.svg | MDF 3 mm: las 5 caras de la caja (rojo = corte, azul = grabado de cerebro) |

## imprimir/ (PLA, capa 0,2 mm, 2–3 paredes, 15 % de relleno; ~38 cm³ en total; sin soportes)
| Archivo | Cant. | Cómo ponerlo en la cama | Cómo se fija |
|---|---|---|---|
| pata_trasera.stl | 1 | Acostada de lado (perfil parejo de 8 mm) | 2 clips a presión, como los ganchos |
| gancho.stl | 2 | Acostado de lado (perfil parejo de 8 mm) | Clip a presión en su ranura |
| cuna_izquierda / cuna_derecha / cuna_atras.stl | 1 c/u | Paradas, como van | M3 × 12 desde abajo, pasando por un tapón; rosca en la pieza |
| soporte_uno.stl, soporte_pca.stl | 1 c/u | Planos, postes arriba | M3 × 10 desde abajo, pasando por un tapón; las placas con M3 × 8 autorroscantes |
| capsula_usbc_cuerpo.stl + capsula_usbc_tapa.stl | 1 c/u | Cuerpo tal cual (base abajo); tapa ya viene dada vuelta | El módulo USB-C entra desde arriba en el cuerpo; la tapa lo aprieta y se cierra con 2 M3 × 16 en las orejas. La pestaña va a la pared de atrás de la caja con 2 M3 × 10 + tuerca; los cables salen por atrás |
| abrazadera_mesa.stl | 1 | Parada, como va (sin soportes) | Se engancha en el borde de atrás de la base; lleva una tuerca M8 atrapada abajo |
| pie_mesa.stl | 1 | Plano | Tuerca M8 atrapada; fieltro abajo. Girándolo se ajusta la altura |
| tapon.stl | 10 | Con la pestaña sobre la cama | Entra desde abajo en cada ranura chica: la llena, centra el tornillo y hace de golilla |

Tornillería: 6 M3 × 10 + 2 tuercas, 2 M3 × 16 (cierre de la cápsula USB-C), 6 M3 × 12, 8 M3 × 8 (placas). Un fieltro o goma de ~1 mm en la cara de la pata que toca la pantalla.

Las ranuras del acrílico son rectangulares (eran para clips): los tornillos pasan por ellas. Las
seis grandes de adelante son para los clips de los ganchos y de la pata; las diez chicas llevan tapones.

## Armado
La base queda fija y horizontal: es una pinza en U (ganchos adelante, pata atrás) con un ángulo de
15° que sigue la pantalla echada, así el peso no le hace palanca. Hecha para el MacBook Air
(borde de 4,5 mm + 1 mm de fieltro).
1. Meter los ganchos desde abajo en sus ranuras de adelante (hacen clic).
2. Meter la pata trasera desde abajo en las 2 ranuras del centro (hace clic) y pegarle un fieltro en la punta.
3. Poner los tapones desde abajo en las ranuras chicas y atornillar la cuna a través de ellos,
   con la base del EyeMech puesta adentro para que quede alineada.
4. Atornillar igual los soportes de las placas, y la UNO y la PCA9685 encima.
5. Armar la caja con la cara grabada hacia afuera y pegarla (cola fría) y meter sus dientes de abajo en las ranuras de atrás.
6. Calzar en la pantalla desde arriba: los ganchos por delante y la pata por detrás.

## Pata hasta la mesa
Para que el peso no venza la bisagra del computador: varilla roscada M8 de 25 cm (cortarla a
~22 cm) + 2 tuercas M8. La varilla se atornilla en la abrazadera (que queda enganchada al borde de
atrás de la base) y abajo en el pie, que se apoya en la mesa detrás del computador. Ajustar el pie
hasta que la base quede horizontal y apriete un poco contra el acrílico.

Placas: la UNO y la PCA9685 se atornillan con M3 × 6 (más largo toca el acrílico). El tetón de
adelante del soporte de la UNO va con M3 × 8 (queda bajito, bajo el conector ICSP).
