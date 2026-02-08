from machine import Pin
import time, deepsleep

def blink():
    led = Pin("LED", Pin.OUT)   # su RP2040/Pico funziona così

    for _ in range(6):
        led.on()
        time.sleep_ms(100)
        led.off()
        time.sleep_ms(100)
        
        

def main():
    time.sleep_ms(3000)
    deepsleep.powmanInit(1704067200)

    blink()
    
    deepsleep.powmanOffForMs(2000)
    
main()