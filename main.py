from machine import Pin
import time, deepsleep


# GPIO used for the visual indicator instead of "LED": on Pico 2 W, "LED" is
# wired through the CYW43 wireless chip (SPI), not a plain RP2350 pad, so
# touching it powers that chip up and skews any power measurement. Wire an
# LED (+ resistor) to this pin, or swap back to Pin("LED", ...) if you only
# care about functional correctness right now, not the current draw.
INDICATOR_GPIO = 2


def blink(indicator, times):
    for _ in range(times):
        indicator.on();  time.sleep_ms(200)
        indicator.off(); time.sleep_ms(200)


def main():
    time.sleep_ms(3000)

    reason = deepsleep.powmanGetWakeupReason()  # before powmanInit()!

    indicator = Pin(INDICATOR_GPIO, Pin.OUT)
    if reason & deepsleep.WAKEUP_GPIO0:
        blink(indicator, 1)   # woken up by GP8
    elif reason & deepsleep.WAKEUP_GPIO1:
        blink(indicator, 2)   # woken up by GP9
    elif reason & deepsleep.WAKEUP_GPIO2:
        blink(indicator, 3)   # woken up by GP10
    elif reason & deepsleep.WAKEUP_GPIO3:
        blink(indicator, 4)   # woken up by GP11
    elif reason & deepsleep.WAKEUP_ALARM:
        blink(indicator, 5)   # woken up by timer alarm
    else:
        blink(indicator, 6)   # fresh boot / other

    deepsleep.powmanInit(1704067200, lowPowerXosc=True, lowPowerRosc=True,
                         lowPowerPlls=True, lowPowerUsbPhy=True, lowPowerWifiChip=True)

    deepsleep.powmanOffForMsOrGPIO(10000, [(8, True), (9, True), (10, True), (11, True)])

main()