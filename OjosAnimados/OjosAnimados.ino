// Ojos animados con PCA9685: miran a lugares al azar, parpadean y hacen expresiones.
// Los valores de calibración vienen de calibracion.md.
// Órdenes por serie (115200), una por línea:
//   M x y   fija la mirada, x e y en -100..100
//           (x: -100 su derecha, +100 su izquierda; y: -100 abajo, +100 arriba).
//           Si deja de recibirlas por 1,5 s vuelve a mirar al azar.
//   E n     hace la expresión n (1..14, ver lista Expresion; 12 = un parpadeo); E 0 corta la actual
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm(0x40);

const int PULSO_MIN = 600;   // µs a 0°
const int PULSO_MAX = 2400;  // µs a 180°

// Canales
const uint8_t INF_DER = 0, SUP_DER = 1, OJOS_Y = 2, INF_IZQ = 3, SUP_IZQ = 4, OJOS_X = 5;   // 3 y 4 cruzados al rearmar

// Párpados: ángulo abierto y cerrado
const float ABIERTO[6] = {55, 140, 0, 140, 25, 0};   // 10° menos que el tope, para no forzar al abrir
const float CERRADO[6] = {138, 42, 0, 30, 135, 0};

// Ojos: centro y extremos
const float X_DER = 40, X_CENTRO = 90, X_IZQ = 130;   // canal 5
const float Y_ABAJO = 0, Y_CENTRO = 100, Y_ARRIBA = 180; // canal 2 (centro recalibrado: mira derecho con la pantalla a 90°)

// Cuánto se alejan los ojos del centro en uso normal (1 = hasta el tope)
const float ALCANCE_X = 0.85;
const float ALCANCE_Y = 0.7;

// Apertura normal de los párpados (1 = abiertos del todo, se reserva para la sorpresa)
const float APERTURA_NORMAL = 0.85;

// Apertura máxima de los párpados cuando los ojos están en el extremo
// (para que no choquen): superiores a 90° mirando abajo, inferiores a 110°/70° mirando arriba
const float APERTURA_SUP_ABAJO = 0.33;
const float APERTURA_INF_ARRIBA = 0.13;

// Suavizado por paso de 20 ms (más alto = más rápido)
const float VEL_OJOS = 0.30;
const float VEL_PARPADOS = 0.55;
// Los párpados avanzan en "apertura" (0 cerrado, 1 abierto), todos a la misma velocidad: así los
// dos ojos cierran y abren juntos aunque cada servo recorra un ángulo distinto. 0,09 por paso de
// 20 ms = ~220 ms de abierto a cerrado, lo que alcanza a hacer el servo más lento.
const float PASO_PARPADO = 0.09;

float actual[6], objetivo[6];

// Mirada: -1..1. x: -1 su derecha, +1 su izquierda. y: -1 abajo, +1 arriba
float miradaX = 0, miradaY = 0;
float apertura = APERTURA_NORMAL;  // 1 abierto, 0 cerrado (sin contar el parpadeo)

// Parpadeo
enum EstadoParpadeo { NADA, CERRANDO, CERRADO_ESPERA, ABRIENDO };
EstadoParpadeo parpadeo = NADA;
unsigned long tParpadeo = 0, proximoParpadeo = 0, proximaMirada = 0;
bool parpadeoDoble = false;

// Expresiones
enum Expresion { NINGUNA, SORPRESA, SUENO, ENOJO, SOSPECHA, GUINO, CURIOSO, FELIZ, RODAR, ALREDEDOR,
                 PENSAR, TRISTE, PARPADEO, CONFUNDIDO, NERVIOSO, DORMIDO, DESPIERTA, NUM_EXPRESIONES };
const unsigned long DURACION[NUM_EXPRESIONES] = {0, 2000, 6500, 3500, 4500, 700, 3000, 2500, 1800, 2600,
                                                 8000, 3500, 0, 3500, 3000, 1, 2000};  // DORMIDO no termina solo

// Las que no se eligen solas al azar: pensar depende de la conversación y parpadeo es una orden
bool soloAPedido(Expresion e) { return e == PENSAR || e == PARPADEO || e == DORMIDO || e == DESPIERTA; }
Expresion expresion = NINGUNA;
unsigned long tExpresion = 0, proximaExpresion = 0;
int8_t lado = 1;  // +1 ojo derecho / -1 ojo izquierdo, para guiño y curioso

// Mirada controlada desde el computador
const unsigned long TIEMPO_SIN_ORDENES = 1500;
unsigned long ultimaOrden = 0;
unsigned long ultimoMensaje = 0;   // cualquier orden del computador (para salir de DORMIDO si se cierra)
bool controlExterno = false;
char linea[24];
uint8_t largoLinea = 0;

void escribir(uint8_t canal, float angulo) {
  angulo = constrain(angulo, -10, 190);   // 500–2500 µs: los SG90 aguantan un poco más que 0–180°
  pwm.writeMicroseconds(canal, PULSO_MIN + (PULSO_MAX - PULSO_MIN) * angulo / 180.0);
}

float mezclar(float a, float b, float t) { return a + (b - a) * t; }

// 0 antes de t0, 1 después de t1, lineal entremedio
float rampa(unsigned long t, unsigned long t0, unsigned long t1) {
  if (t <= t0) return 0;
  if (t >= t1) return 1;
  return float(t - t0) / (t1 - t0);
}

float anguloParpado(uint8_t canal, float apert) {
  return mezclar(CERRADO[canal], ABIERTO[canal], constrain(apert, 0, 1));
}

void iniciarExpresion(Expresion e, unsigned long ahora) {
  if (e == PARPADEO) {  // no es una expresión que dure: solo un parpadeo ahora
    if (parpadeo == NADA) iniciarParpadeo(ahora);
    return;
  }
  expresion = e;
  tExpresion = ahora;
  lado = random(2) ? 1 : -1;
}

void programarExpresion(unsigned long ahora) {
  proximaExpresion = ahora + (controlExterno ? random(15000, 35000) : random(8000, 20000));
}

void iniciarParpadeo(unsigned long ahora) {
  parpadeo = CERRANDO;
  tParpadeo = ahora;
  parpadeoDoble = random(100) < 15;
}

void nuevaMirada(unsigned long ahora) {
  if (random(100) < 30) {
    // A veces vuelve al frente
    miradaX = random(-15, 16) / 100.0;
    miradaY = random(-10, 11) / 100.0;
  } else {
    miradaX = random(-100, 101) / 100.0 * ALCANCE_X;
    miradaY = random(-100, 101) / 100.0 * ALCANCE_Y;
  }
  // De vez en cuando entrecierra los ojos
  apertura = random(100) < 15 ? random(45, 75) / 100.0 : APERTURA_NORMAL;
  // Muchas veces parpadea al cambiar de mirada, como las personas
  if (random(100) < 35 && parpadeo == NADA) iniciarParpadeo(ahora);
  proximaMirada = ahora + random(600, 3500);
}

float actualizarParpadeo(unsigned long ahora) {
  unsigned long t = ahora - tParpadeo;
  switch (parpadeo) {
    case CERRANDO:
      if (t > 230) { parpadeo = CERRADO_ESPERA; tParpadeo = ahora; }   // alcanza a cerrar del todo
      return 0;
    case CERRADO_ESPERA:
      if (t > 60) { parpadeo = ABRIENDO; tParpadeo = ahora; }
      return 0;
    case ABRIENDO:
      if (t > 240) {
        if (parpadeoDoble) { parpadeoDoble = false; parpadeo = CERRANDO; tParpadeo = ahora; return 0; }
        parpadeo = NADA;
        proximoParpadeo = ahora + random(2000, 6000);
      }
      return 1;
    default:
      // Durante el guiño y el sueño no parpadea solo
      if (ahora >= proximoParpadeo && expresion != GUINO && expresion != SUENO && expresion != DORMIDO &&
          expresion != DESPIERTA) iniciarParpadeo(ahora);
      return 1;
  }
}

void leerSerie(unsigned long ahora) {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      linea[largoLinea] = 0;
      if (largoLinea > 0) ultimoMensaje = ahora;
      int x, y;
      if (largoLinea > 0 && sscanf(linea, "M %d %d", &x, &y) == 2) {
        float nx = constrain(x, -100, 100) / 100.0;
        float ny = constrain(y, -100, 100) / 100.0;
        if (!controlExterno) {
          // Apareció alguien: se alegra o se sorprende
          if (expresion == NINGUNA) iniciarExpresion(random(100) < 60 ? FELIZ : SORPRESA, ahora);
          programarExpresion(ahora);
        } else if (abs(nx - miradaX) + abs(ny - miradaY) > 0.8) {
          // Un salto grande de mirada provoca a veces un parpadeo
          if (random(100) < 40 && parpadeo == NADA) iniciarParpadeo(ahora);
        }
        miradaX = nx * ALCANCE_X;
        miradaY = ny * ALCANCE_Y;
        apertura = APERTURA_NORMAL;
        controlExterno = true;
        ultimaOrden = ahora;
      } else if (largoLinea == 1 && linea[0] == 'D') {   // diagnóstico: ángulos actuales
        Serial.print(F("expr ")); Serial.print(expresion); Serial.print(F(" ext ")); Serial.print(controlExterno);
        for (uint8_t i = 0; i < 6; i++) { Serial.print(' '); Serial.print(actual[i], 1); }
        Serial.println();
      } else if (largoLinea > 0 && sscanf(linea, "E %d", &x) == 1 && x >= 0 && x < NUM_EXPRESIONES) {
        if (x == NINGUNA) {
          expresion = NINGUNA;
          programarExpresion(ahora);
        } else {
          iniciarExpresion((Expresion)x, ahora);
        }
      }
      largoLinea = 0;
    } else if (largoLinea < sizeof(linea) - 1) {
      linea[largoLinea++] = c;
    }
  }
  if (controlExterno && ahora - ultimaOrden > TIEMPO_SIN_ORDENES) {
    controlExterno = false;
    proximaMirada = ahora;
  }
}

void calcularObjetivos(unsigned long ahora, float factorParpadeo) {
  float gx = miradaX, gy = miradaY;
  float supD = apertura, supI = apertura, infD = apertura, infI = apertura;
  float velOjos = VEL_OJOS;

  if (expresion != NINGUNA) {
    unsigned long t = ahora - tExpresion;
    float p = float(t) / DURACION[expresion];
    switch (expresion) {
      case DESPIERTA: {  // abre despacio y adormilado, parpadea, y abre bien mirando a la persona
        float a;
        if (t < 700) a = 0.45 * rampa(t, 0, 700);
        else if (t < 950) a = 0.45 * (1 - rampa(t, 700, 950));
        else a = mezclar(0, 1, rampa(t, 950, 1400));
        supD = supI = infD = infI = a;
        gx = miradaX;
        gy = t < 950 ? mezclar(-0.25, miradaY, rampa(t, 0, 950)) : miradaY;
        velOjos = t < 950 ? 0.06 : VEL_OJOS;
        break;
      }
      case DORMIDO: {  // ojos cerrados, mirando un poco abajo, con un leve movimiento de sueño
        supD = supI = infD = infI = 0;
        gy = -0.25;
        gx = 0.12 * sin(t / 2300.0);
        velOjos = 0.03;
        break;
      }
      case SORPRESA:  // abre todo y mira un poco hacia arriba
        supD = supI = infD = infI = 1;
        gy = min(1.0f, miradaY + 0.25f);
        break;
      case SUENO: {   // los párpados caen despacio, cabecea y despierta de golpe
        float caida = rampa(t, 0, 3500);
        supD = supI = mezclar(apertura, 0.12, caida);
        gy = mezclar(miradaY, -0.35, caida);
        velOjos = 0.08;
        if (t > 4800) { supD = supI = infD = infI = 1; gy = 0.1; velOjos = VEL_OJOS; }
        break;
      }
      case ENOJO:     // entrecierra arriba y abajo
        supD = supI = 0.38;
        infD = infI = 0.5;
        break;
      case SOSPECHA:  // entrecierra y mira de lado a lado despacio, alrededor de donde miraba
        supD = supI = 0.45;
        infD = infI = 0.55;
        gx = miradaX + (controlExterno ? 0.3 : 0.7) * sin(TWO_PI * t / 3000.0);
        gy = controlExterno ? miradaY : 0;
        velOjos = 0.15;
        break;
      case GUINO:     // cierra un solo ojo
        if (t > 100 && t < 400) {
          if (lado > 0) supD = infD = 0; else supI = infI = 0;
        }
        break;
      case CURIOSO:   // un ojo entrecerrado y la mirada un poco de lado
        if (lado > 0) { supD = 0.45; infD = 0.6; supI = infI = 1; }
        else          { supI = 0.45; infI = 0.6; supD = infD = 1; }
        // Si está mirando a alguien, no le quita la mirada: solo la corre un poco
        gx = controlExterno ? miradaX - 0.12 * lado : -0.4 * lado;
        gy = controlExterno ? miradaY + 0.1 : 0.15;
        break;
      case FELIZ:     // suben los párpados inferiores, como ojos sonrientes
        supD = supI = 0.9;
        infD = infI = 0.4;
        break;
      case RODAR: {   // da una vuelta con los ojos
        float radio = min(1.0f, min(p / 0.15f, (1 - p) / 0.15f));
        float a = TWO_PI * p;
        gx = 0.85 * radio * cos(a) * lado;
        gy = 0.75 * radio * sin(a);
        supD = supI = 0.75;
        break;
      }
      case ALREDEDOR: // mira rápido a un lado y al otro
        gx = t < 700 ? -0.8 : (t < 1500 ? 0.8 : 0);
        gy = 0;
        velOjos = 0.35;
        break;
      case PENSAR:    // mira hacia arriba y a un lado, con los ojos algo entrecerrados
        gx = 0.45 * lado;
        gy = 0.55;
        supD = supI = 0.75;
        velOjos = 0.12;
        break;
      case TRISTE:    // mirada baja y párpados caídos
        gy = controlExterno ? miradaY - 0.3 : -0.45;
        gx = controlExterno ? miradaX : miradaX * 0.3;
        supD = supI = 0.45;
        velOjos = 0.08;
        break;
      case CONFUNDIDO: {  // un párpado arriba y el otro abajo; la mirada duda, con pausas
        const float dudas[4] = {-0.22, 0.18, -0.08, 0.14};
        gx = miradaX + dudas[(t / 700) % 4] * lado;
        gy = miradaY + 0.1;
        if (lado > 0) { supD = 1.0; supI = 0.45; infI = 0.7; }
        else          { supI = 1.0; supD = 0.45; infD = 0.7; }
        velOjos = 0.2;
        break;
      }
      case NERVIOSO:   // miradas rápidas de un lado a otro, párpados temblando un poco y parpadeos
        gx = miradaX + ((t / 330) % 2 ? 0.32 : -0.32) * lado;
        gy = miradaY + ((t / 990) % 2 ? 0.08 : -0.04);
        supD = supI = 0.8 + 0.05 * sin(TWO_PI * t / 160.0);  // temblor chico, seguro para los servos
        velOjos = 0.45;
        if (t % 1100 < 20 && parpadeo == NADA) iniciarParpadeo(ahora);
        break;
      default:
        break;
    }
    // Dormido sigue mientras el computador lo pida (seguir.py repite la orden cada 10 s); si se
    // cerró el programa, despierta solo a los 15 s y vuelve a animarse por su cuenta
    if (expresion == DORMIDO && ahora - ultimoMensaje > 15000) {
      expresion = NINGUNA;
      programarExpresion(ahora);
    }
    if (expresion != DORMIDO && expresion != NINGUNA && t >= DURACION[expresion]) {
      expresion = NINGUNA;
      programarExpresion(ahora);
      proximaMirada = ahora + 300;
    }
  }

  gx = constrain(gx, -1, 1);
  gy = constrain(gy, -1, 1);
  objetivo[OJOS_X] = gx < 0 ? mezclar(X_CENTRO, X_DER, -gx) : mezclar(X_CENTRO, X_IZQ, gx);
  objetivo[OJOS_Y] = gy < 0 ? mezclar(Y_CENTRO, Y_ABAJO, -gy) : mezclar(Y_CENTRO, Y_ARRIBA, gy);

  // Los párpados acompañan la mirada para no chocar con los ojos
  float maxSup = gy < 0 ? mezclar(1, APERTURA_SUP_ABAJO, -gy) : 1;
  float maxInf = gy > 0 ? mezclar(1, APERTURA_INF_ARRIBA, gy) : 1;

  objetivo[SUP_DER] = anguloParpado(SUP_DER, min(supD, maxSup) * factorParpadeo);
  objetivo[SUP_IZQ] = anguloParpado(SUP_IZQ, min(supI, maxSup) * factorParpadeo);
  objetivo[INF_DER] = anguloParpado(INF_DER, min(infD, maxInf) * factorParpadeo);
  objetivo[INF_IZQ] = anguloParpado(INF_IZQ, min(infI, maxInf) * factorParpadeo);

  // La velocidad de los ojos depende de la expresión
  actual[OJOS_X] += (objetivo[OJOS_X] - actual[OJOS_X]) * velOjos;
  actual[OJOS_Y] += (objetivo[OJOS_Y] - actual[OJOS_Y]) * velOjos;
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
  randomSeed(analogRead(A0));

  calcularObjetivos(millis(), 1);
  for (uint8_t i = 0; i < 6; i++) {
    actual[i] = objetivo[i];
    escribir(i, actual[i]);
  }
  proximoParpadeo = millis() + 1500;
  proximaMirada = millis() + 1000;
  programarExpresion(millis());
}

void loop() {
  static unsigned long ultimoPaso = 0;
  unsigned long ahora = millis();
  leerSerie(ahora);
  if (ahora - ultimoPaso < 20) return;
  ultimoPaso = ahora;

  if (expresion == NINGUNA && ahora >= proximaExpresion) {
    Expresion e;
    do { e = (Expresion)random(1, NUM_EXPRESIONES); } while (soloAPedido(e));
    iniciarExpresion(e, ahora);
  }
  if (!controlExterno && expresion == NINGUNA && ahora >= proximaMirada) nuevaMirada(ahora);
  calcularObjetivos(ahora, actualizarParpadeo(ahora));

  for (uint8_t i = 0; i < 6; i++) {
    if (i != OJOS_X && i != OJOS_Y) {
      float rango = ABIERTO[i] - CERRADO[i];
      float ap = (actual[i] - CERRADO[i]) / rango, apObj = (objetivo[i] - CERRADO[i]) / rango;
      ap += constrain(apObj - ap, -PASO_PARPADO, PASO_PARPADO);
      actual[i] = CERRADO[i] + rango * ap;
    }
    escribir(i, actual[i]);
  }
}
