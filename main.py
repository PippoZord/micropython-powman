from machine import Pin
import time, deepsleep
        
        

def main():
    time.sleep_ms(3000)

    reason = deepsleep.powmanGetWakeupReason()

    led = Pin("LED", Pin.OUT)
    if reason & deepsleep.WAKEUP_GPIO0:
        blinks = 1   # woken up by GP8
    elif reason & deepsleep.WAKEUP_GPIO1:
        blinks = 2   # woken up by GP9
    elif reason & deepsleep.WAKEUP_GPIO2:
        blinks = 3   # woken up by GP10
    elif reason & deepsleep.WAKEUP_GPIO3:
        blinks = 4   # woken up by GP11
    elif reason & deepsleep.WAKEUP_ALARM:
        blinks = 5   # woken up by allarme
    else:
        blinks = 6   # normal boot / other

    for _ in range(blinks):
        led.on(); time.sleep_ms(200)
        led.off(); time.sleep_ms(200)

    deepsleep.powmanInit(1704067200)
    deepsleep.powmanOffForMsOrGPIO(10000, [(8, True), (9, True), (10, True), (11, True)])

main()