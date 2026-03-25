// Test Rig Hardware Validation Sketch
//
// Pin assignments (from test_rig.yaml):
//   Servo:      GPIO 18 (PWM)
//   DC Motor:   GPIO 25 (ENA/PWM), GPIO 26 (IN1), GPIO 27 (IN2) - L298N
//   Stepper:    GPIO 32 (STEP), GPIO 33 (DIR) - A4988
//   IMU:        GPIO 21 (SDA), GPIO 22 (SCL) - I2C
//   Ultrasonic: GPIO 4 (TRIG), GPIO 5 (ECHO)
//
// Serial Commands (115200 baud):
//   servo <angle>     - Move servo (0-180)
//   motor <speed>     - DC motor speed (-100 to 100)
//   step <steps>      - Move stepper (negative = reverse)
//   distance          - Read ultrasonic distance
//   imu               - Read IMU data
//   demo              - Run demo sequence
//   stop              - Stop all motors
//   help              - Show commands

#include <ESP32Servo.h>
#include <Wire.h>

// Pin Definitions
#define SERVO_PIN       18

// DC Motor (L298N)
#define MOTOR_ENA_PIN   25
#define MOTOR_IN1_PIN   26
#define MOTOR_IN2_PIN   27

// Stepper (A4988)
#define STEPPER_STEP_PIN 32
#define STEPPER_DIR_PIN  33
#define STEPPER_EN_PIN   -1  // Set to actual pin if wired, or -1 if tied to GND

// Ultrasonic (HC-SR04)
#define ULTRA_TRIG_PIN   4
#define ULTRA_ECHO_PIN   5

// IMU (MPU6050)
#define IMU_ADDR        0x68
#define IMU_SDA_PIN     21
#define IMU_SCL_PIN     22

// PWM Configuration
#define MOTOR_PWM_FREQ  5000
#define MOTOR_PWM_RES   8

// Global Objects
Servo servo;
String inputBuffer = "";
bool imuAvailable = false;

// Initialization
void setupServo() {
    servo.attach(SERVO_PIN);
    servo.write(90);
    Serial.println("[OK] Servo initialized on GPIO 18");
}

void setupDCMotor() {
    pinMode(MOTOR_IN1_PIN, OUTPUT);
    pinMode(MOTOR_IN2_PIN, OUTPUT);
    pinMode(MOTOR_ENA_PIN, OUTPUT);

    // New ESP32 Arduino core API (3.x)
    ledcAttach(MOTOR_ENA_PIN, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcWrite(MOTOR_ENA_PIN, 0);

    digitalWrite(MOTOR_IN1_PIN, LOW);
    digitalWrite(MOTOR_IN2_PIN, LOW);

    Serial.println("[OK] DC Motor initialized on GPIO 25/26/27");
}

void setupStepper() {
    pinMode(STEPPER_STEP_PIN, OUTPUT);
    pinMode(STEPPER_DIR_PIN, OUTPUT);
    digitalWrite(STEPPER_STEP_PIN, LOW);
    digitalWrite(STEPPER_DIR_PIN, LOW);

    // Enable pin (active LOW) - set to -1 if hardwired to GND
    if (STEPPER_EN_PIN >= 0) {
        pinMode(STEPPER_EN_PIN, OUTPUT);
        digitalWrite(STEPPER_EN_PIN, LOW);  // Enable the driver
    }
    Serial.println("[OK] Stepper initialized on GPIO 32/33");
}

void setupUltrasonic() {
    pinMode(ULTRA_TRIG_PIN, OUTPUT);
    pinMode(ULTRA_ECHO_PIN, INPUT);
    digitalWrite(ULTRA_TRIG_PIN, LOW);
    Serial.println("[OK] Ultrasonic initialized on GPIO 4/5");
}

void setupIMU() {
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);

    Wire.beginTransmission(IMU_ADDR);
    Wire.write(0x6B);
    Wire.write(0x00);
    uint8_t error = Wire.endTransmission();

    if (error == 0) {
        imuAvailable = true;
        Serial.println("[OK] IMU (MPU6050) initialized on GPIO 21/22");
    } else {
        imuAvailable = false;
        Serial.println("[WARN] IMU not detected on I2C bus");
    }
}

// Actuator Control
void setServo(int angle) {
    angle = constrain(angle, 0, 180);
    servo.write(angle);
    Serial.print("Servo -> ");
    Serial.print(angle);
    Serial.println(" degrees");
}

void setDCMotor(int speed) {
    speed = constrain(speed, -100, 100);
    int pwmVal = map(abs(speed), 0, 100, 0, 255);

    if (speed > 0) {
        digitalWrite(MOTOR_IN1_PIN, HIGH);
        digitalWrite(MOTOR_IN2_PIN, LOW);
        ledcWrite(MOTOR_ENA_PIN, pwmVal);
        Serial.print("DC Motor -> ");
        Serial.print(speed);
        Serial.println("% forward");
    } else if (speed < 0) {
        digitalWrite(MOTOR_IN1_PIN, LOW);
        digitalWrite(MOTOR_IN2_PIN, HIGH);
        ledcWrite(MOTOR_ENA_PIN, pwmVal);
        Serial.print("DC Motor -> ");
        Serial.print(-speed);
        Serial.println("% reverse");
    } else {
        digitalWrite(MOTOR_IN1_PIN, LOW);
        digitalWrite(MOTOR_IN2_PIN, LOW);
        ledcWrite(MOTOR_ENA_PIN, 0);
        Serial.println("DC Motor -> stopped");
    }
}

void stepMotor(int steps) {
    if (steps == 0) return;

    // Clear any pending serial data before starting
    while (Serial.available()) Serial.read();

    digitalWrite(STEPPER_DIR_PIN, steps > 0 ? HIGH : LOW);
    delay(1);  // Direction setup time

    int absSteps = abs(steps);

    Serial.print("Stepper -> ");
    Serial.print(absSteps);
    Serial.println(steps > 0 ? " steps forward" : " steps reverse");

    for (int i = 0; i < absSteps; i++) {
        digitalWrite(STEPPER_STEP_PIN, HIGH);
        delayMicroseconds(500);
        digitalWrite(STEPPER_STEP_PIN, LOW);
        delayMicroseconds(500);

        // Check for abort every 100 steps
        if (i % 100 == 0 && i > 0 && Serial.available()) {
            Serial.println("Stepper interrupted by user");
            while (Serial.available()) Serial.read();
            break;
        }
    }
    Serial.println("Stepper done");
}

void stopAll() {
    servo.write(90);
    setDCMotor(0);
    Serial.println("All motors stopped");
}

// Sensor Reading
float readUltrasonic() {
    digitalWrite(ULTRA_TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(ULTRA_TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(ULTRA_TRIG_PIN, LOW);

    long duration = pulseIn(ULTRA_ECHO_PIN, HIGH, 30000);

    if (duration == 0) {
        Serial.println("Ultrasonic: timeout (no echo)");
        return -1;
    }

    float distance = duration * 0.0343 / 2.0;
    Serial.print("Distance: ");
    Serial.print(distance, 1);
    Serial.println(" cm");
    return distance;
}

void scanI2C() {
    Serial.println("Scanning I2C bus...");
    int found = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print("  Found device at 0x");
            if (addr < 16) Serial.print("0");
            Serial.println(addr, HEX);
            found++;
        }
    }
    if (found == 0) {
        Serial.println("  No I2C devices found!");
        Serial.println("  Check: SDA=GPIO21, SCL=GPIO22, power, pull-ups");
    } else {
        Serial.print("  Total: ");
        Serial.print(found);
        Serial.println(" device(s)");
    }
}

void readIMU() {
    if (!imuAvailable) {
        Serial.println("IMU not available - try 'scan' to check I2C bus");
        return;
    }

    int16_t ax, ay, az, gx, gy, gz;

    Wire.beginTransmission(IMU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(IMU_ADDR, 14);

    ax = Wire.read() << 8 | Wire.read();
    ay = Wire.read() << 8 | Wire.read();
    az = Wire.read() << 8 | Wire.read();
    Wire.read(); Wire.read();
    gx = Wire.read() << 8 | Wire.read();
    gy = Wire.read() << 8 | Wire.read();
    gz = Wire.read() << 8 | Wire.read();

    float accel_scale = 16384.0;
    float gyro_scale = 131.0;

    Serial.println("IMU Reading:");
    Serial.print("  Accel: X="); Serial.print(ax/accel_scale, 2);
    Serial.print(" Y="); Serial.print(ay/accel_scale, 2);
    Serial.print(" Z="); Serial.print(az/accel_scale, 2);
    Serial.println(" g");
    Serial.print("  Gyro:  X="); Serial.print(gx/gyro_scale, 1);
    Serial.print(" Y="); Serial.print(gy/gyro_scale, 1);
    Serial.print(" Z="); Serial.print(gz/gyro_scale, 1);
    Serial.println(" deg/s");
}

// Demo Sequence
void runDemo() {
    Serial.println("\n=== Starting Demo Sequence ===\n");

    Serial.println("1. Servo sweep...");
    for (int angle = 0; angle <= 180; angle += 30) {
        setServo(angle);
        delay(300);
    }
    setServo(90);
    delay(500);

    Serial.println("\n2. DC motor test...");
    setDCMotor(50);
    delay(1000);
    setDCMotor(-50);
    delay(1000);
    setDCMotor(0);
    delay(500);

    Serial.println("\n3. Stepper test...");
    stepMotor(200);
    delay(500);
    stepMotor(-200);
    delay(500);

    Serial.println("\n4. Sensor readings...");
    readUltrasonic();
    readIMU();

    Serial.println("\n=== Demo Complete ===\n");
}

// Command Parser
void printHelp() {
    Serial.println("\n=== Test Rig Commands ===");
    Serial.println("  servo <0-180>      Move servo to angle");
    Serial.println("  motor <-100..100>  Set DC motor speed");
    Serial.println("  step <steps>       Move stepper (negative=reverse)");
    Serial.println("  distance           Read ultrasonic sensor");
    Serial.println("  imu                Read IMU data");
    Serial.println("  scan               Scan I2C bus for devices");
    Serial.println("  demo               Run demo sequence");
    Serial.println("  stop               Stop all motors");
    Serial.println("  help               Show this help");
    Serial.println("==========================\n");
}

void processCommand(String cmd) {
    cmd.trim();
    cmd.toLowerCase();

    if (cmd.startsWith("servo ")) {
        int angle = cmd.substring(6).toInt();
        setServo(angle);
    }
    else if (cmd.startsWith("motor ")) {
        int speed = cmd.substring(6).toInt();
        setDCMotor(speed);
    }
    else if (cmd.startsWith("step ")) {
        int steps = cmd.substring(5).toInt();
        stepMotor(steps);
    }
    else if (cmd == "distance" || cmd == "dist") {
        readUltrasonic();
    }
    else if (cmd == "imu") {
        readIMU();
    }
    else if (cmd == "scan") {
        scanI2C();
    }
    else if (cmd == "demo") {
        runDemo();
    }
    else if (cmd == "stop") {
        stopAll();
    }
    else if (cmd == "help" || cmd == "?") {
        printHelp();
    }
    else if (cmd.length() > 0) {
        Serial.print("Unknown command: '");
        Serial.print(cmd);
        Serial.println("' (type 'help' for commands)");
    }
}

// Main
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n");
    Serial.println("========================================");
    Serial.println("  Test Rig Hardware Validation Sketch");
    Serial.println("========================================\n");

    setupServo();
    setupDCMotor();
    setupStepper();
    setupUltrasonic();
    setupIMU();

    Serial.println("\nReady! Type 'help' for commands.\n");
}

void loop() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                processCommand(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
        }
    }
}
