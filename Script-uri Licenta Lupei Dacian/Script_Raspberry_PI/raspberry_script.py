import time
import threading
import queue
import RPi.GPIO as GPIO
from hx711 import HX711
from RPLCD.i2c import CharLCD
import zenoh
from cryptography.fernet import Fernet

# Criptologie 
key = b'91uKPT7BqEWdPpOA1pAY-leCrrG9bhk9PEVNeIQi7BM='
cipher = Fernet(key)

# GPIO 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Load Cell (HX711 1 kg max)
DOUT = 21
SCK = 20
hx = HX711(DOUT, SCK)
hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(1826.23)
hx.reset()
hx.tare()

# Ultrasonic senzor
TRIG = 8
ECHO = 7
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Motoare (L298N)
motor_left_in1 = 27
motor_left_in2 = 18
motor_left_ena = 17
motor_right_in1 = 23
motor_right_in2 = 24
motor_right_ena = 25

motor_pins = [motor_left_in1, motor_left_in2, motor_left_ena,
              motor_right_in1, motor_right_in2, motor_right_ena]
for pin in motor_pins:
    GPIO.setup(pin, GPIO.OUT)

pwm_left = GPIO.PWM(motor_left_ena, 1000)
pwm_right = GPIO.PWM(motor_right_ena, 1000)
pwm_left.start(0)
pwm_right.start(0)

# LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, charmap='A00', auto_linebreaks=True)

# Variabile
speed = 110 * 100 / 255
viteza_mica = 100;
viteza_mare = 150;
punct_A = 8
punct_B = 19

# Thread
movement_thread= None
stop_event = threading.Event()

# Functii 
def map_value(x, in_min, in_max, out_min, out_max):
    return ((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def median_weight(hx, samples=5):
    readings = [hx.get_weight(1) for _ in range(samples)]
    readings.sort()
    return readings[len(readings) // 2]

def read_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.05)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)

def move_to_position(target_distance, speed):
    print(f"Deplasare catre pozitia: {target_distance} cm")
    lcd.clear()
    lcd.write_string(f"Tinta: {target_distance}cm")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Se deplaseaza...")

    distance = read_distance()
    print(f"Distanta: {distance:.2f} cm")

    while not stop_event.is_set() and ((target_distance == punct_B and distance < target_distance) or 
           (target_distance == punct_A and distance > target_distance)):
        if target_distance == punct_A:
            GPIO.output(motor_left_in1, GPIO.LOW)
            GPIO.output(motor_left_in2, GPIO.HIGH)
            GPIO.output(motor_right_in1, GPIO.HIGH)
            GPIO.output(motor_right_in2, GPIO.LOW)
        else:
            GPIO.output(motor_left_in1, GPIO.HIGH)
            GPIO.output(motor_left_in2, GPIO.LOW)
            GPIO.output(motor_right_in1, GPIO.LOW)
            GPIO.output(motor_right_in2, GPIO.HIGH)

        pwm_left.ChangeDutyCycle(speed)
        pwm_right.ChangeDutyCycle(speed)

        distance = read_distance()
        print(f"Merge. Distanta: {distance:.2f} cm")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Dist: {distance:>5.1f} cm  ")
        time.sleep(0.1)

    stop_motors()
    lcd.clear()
    if stop_event.is_set():
        lcd.write_string("Deplasare oprita")
        print("Deplasare oprita")
        send_status(status_pub, "Deplasare oprita")
    else:
        print("Ajuns la destinatie.")
        lcd.write_string("Ajuns la ")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("destinatie")
        print("Ajuns la destinatie.")
        send_status(status_pub, "Am ajuns la destinatie.")
    
    
    
def stop_motors():
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)
    for pin in [motor_left_in1, motor_left_in2, motor_right_in1, motor_right_in2]:
        GPIO.output(pin, GPIO.LOW)
    print("Motoare oprite")

# TELEMETRIE PWM, GREUTATE
def send_telemetry(pub, pwm, weight="N/A"):
    try:
        if isinstance(weight, float):
            weight_str = f"{weight:.2f}"
        else:
            weight_str = str(weight)
        msg = f"PWM:{pwm:.2f},WEIGHT:{weight_str}"
        encrypted_msg = cipher.encrypt(msg.encode())
        pub.put(encrypted_msg)
        print(f"[Zenoh] Trimit telemetrie: {msg}")
    except Exception as e:
        print(f"[Zenoh] Eroare trimitele telemetrie: {e}")

# HEX CODE QUEUE 
command_queue = queue.Queue()

# ZENOH
def on_hex_received(sample):
    try:
        encrypted = bytes(sample.payload)
        decrypted = cipher.decrypt(encrypted)
        hex_str = decrypted.decode().strip()
        print(f"[Zenoh] Primit comanda")
        command_queue.put(hex_str)
    except Exception as e:
        print(f"[Zenoh] Eroare decriptare date: {e}")

def send_status(pub, message):
    try:
        encrypted_msg = cipher.encrypt(message.encode())
        pub.put(encrypted_msg)
        print(f"[Zenoh] Trimis status comanda: {message}")
    except Exception as e:
        print(f"[Zenoh] Eroare trimitere status operatie: {e}")

# Main program
if __name__ == "__main__":
    try:
        lcd.clear()
        lcd.write_string("Astept comanda")
        cfg = zenoh.Config()
        cfg.insert_json5("listen/endpoints", '["tcp/0.0.0.0:7447"]')

        with zenoh.open(cfg) as session:
            sub = session.declare_subscriber("hex/send", on_hex_received)
            telemetry_pub = session.declare_publisher("telemetry/status")
            status_pub = session.declare_publisher("telemetry/statuslog")
            print("Zenoh ready.")

            def process_command(choice):
                global speed, movement_thread
                if choice == '01':
                    speed = viteza_mica * 100 / 255
                    print(f"Viteza mica: {speed:.2f}%")
                    lcd.clear()
                    lcd.write_string("Viteza MICA")
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(f"{speed:.1f}%")
                    send_telemetry(telemetry_pub, speed)

                elif choice == '02':
                    speed = viteza_mare * 100 / 255
                    print(f"Viteza mare: {speed:.2f}%")
                    lcd.clear()
                    lcd.write_string("Viteza MARE")
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(f"{speed:.1f}%")
                    send_telemetry(telemetry_pub, speed)

                elif choice == '03':
                    lcd.clear()
                    lcd.write_string("Plasati obiectul...")
                    print("Plasati obiectul pe cantar.")
                    time.sleep(3)
                    for i in range(5, 0, -1):
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(f"Citire in {i}  ")
                        print(f"{i}...")
                        time.sleep(1)

                    start_time = time.time()
                    duration = 17
                    total_weight = 0
                    samples = 0
                    last_valid = None
                    TOLERANCE = 0.15

                    print("Citire greutate...")
                    lcd.clear()
                    lcd.write_string("Citire greutate")

                    while time.time() - start_time < duration:
                        weight = median_weight(hx)
                        if last_valid is None or last_valid == 0 or abs(weight - last_valid) / last_valid < TOLERANCE:
                            print(f"Greutate curenta: {weight:.2f} g")
                            lcd.cursor_pos = (1, 0)
                            lcd.write_string(f"G: {weight:>5.1f} g  ")
                            total_weight += weight
                            samples += 1
                            last_valid = weight
                        else:
                            print(f"Valoare eronata: {weight:.2f} g")
                        time.sleep(0.1)

                    if samples > 0:
                        avg_weight = total_weight / samples
                        mapped = map_value(avg_weight, 0, 180, 100, 170)
                        speed = max(0, min(mapped, 255)) * 100 / 255
                        print(f"\Greutate medie: {avg_weight:.2f} g")
                        print(f"Viteza corespunzatoare: {speed:.2f}%")
                        lcd.clear()
                        lcd.write_string("Greutate medie")
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(f"Viteza: {speed:.1f}%")
                        send_telemetry(telemetry_pub, speed, avg_weight)
                        send_status(status_pub, "Calculul greutatii reusita")
                    else:
                        print("Nicio valoare corespunzatoare valida.")
                        speed = 0
                        lcd.clear()
                        lcd.write_string("Fara valori valide")
                        send_telemetry(telemetry_pub, 0, "N/A")
                        send_status(status_pub, "Calculul greutatii nereusita")

                elif choice == '04':
                    print("Merge spre A (6cm)")
                    send_status(status_pub, "Moving to point A")
                    stop_event.clear()
                    movement_thread = threading.Thread(target=move_to_position, args=(punct_A, speed))
                    movement_thread.start()
                elif choice == '05':
                    print("Merge spre B (20cm)")
                    send_status(status_pub, "Moving to point B")
                    stop_event.clear()
                    movement_thread = threading.Thread(target=move_to_position, args=(punct_B, speed))
                    movement_thread.start()
                    
                elif choice == '06':
                    print("Oprire motoare")
                    stop_event.set()
                    if movement_thread and movement_thread.is_alive():
                        movement_thread.join(timeout=1)
                    stop_motors()
                    lcd.clear()
                    lcd.write_string("Motoare oprite")
                    send_status(status_pub, "Motoare oprite")
                    
                elif choice == '08':
                    distance = read_distance()
                    print(f"Distanta curenta: {distance:.2f} cm")
                    lcd.clear()
                    lcd.write_string(f"Distanta curenta: {distance:.1f} cm")
                    send_status(status_pub, f"Distanta: {distance:.2f} cm")
                elif choice == '07':
                    print("Comanda de iesire semnalata.")
                    raise SystemExit

                else:
                    print(f"Comanda invalida: {choice}")

            while True:
                try:
                    command = command_queue.get(timeout=0.1)
                    process_command(command)
                except queue.Empty:
                    continue

    except KeyboardInterrupt:
        print("Intrerupere de la utilizator")
    except SystemExit:
        print("Graceful exit")
    finally:
        stop_motors()
        pwm_left.stop()
        pwm_right.stop()
        lcd.clear()
        lcd.write_string("Sistem oprit")
        time.sleep(1)
        GPIO.cleanup()
        print("Sistem oprit")
