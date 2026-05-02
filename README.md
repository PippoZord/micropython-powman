# Powman – Power Management Library for Micropython

The main goal is to reproduce similar low-power timer and wake-up functionalities in [**Micropython**](https://github.com/micropython/micropython). It provides direct access to hardware registers through memory-mapped I/O and is intended for **bare-metal embedded development**.

This project is inspired by and based on the **powman library** implementation available in the [**Raspberry Pi Pico SDK**](https://github.com/raspberrypi/pico-sdk/tree/master) 

The library directly accesses the RP2350 power management and timer registers via memory-mapped I/O. Official documentation can be found in the [**RP2350 datasheet**](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008373-DS-2-rp2350-datasheet.pdf?disposition=inline), especially in Section **6.0** (Power Management Overview and Section **6.4** (Register Configuration)

It is designed to control low-power modes, timers, and wake-up alarms on Raspberry Pi Pico 2.

> [Here](https://github.com/PippoZord/tinygo-powman)  for tinygo library

## Requirements

* Micropython
* Raspberry Pi Pico 2

## Usage

> **Important:** `powmanGetWakeupReason()` must be called **before** `powmanInit()`, because init writes to POWMAN registers that may affect wake-up state.

### 1. Check wake-up reason

```python
import deepsleep

reason = deepsleep.powmanGetWakeupReason()

if reason == 0:
    print("fresh boot")
elif reason & deepsleep.WAKEUP_ALARM:
    print("woke from timer")
elif reason & deepsleep.WAKEUP_GPIO0:
    print("woke from GPIO")
```

### 2. Initialize the timer

Set the absolute system time in milliseconds (must be > 0):

```python
deepsleep.powmanInit(1704067200)
```

### 3. Enter deep sleep

Sleep for a fixed duration (milliseconds):

```python
deepsleep.powmanOffForMs(10000)  # sleep 10 seconds
```

Or sleep until a GPIO goes HIGH:

```python
deepsleep.powmanOffUntilGPIO(15)  # wake on GP15 HIGH
```

Both functions never return — the chip reboots on wake-up.

---

### Full example

```python
import deepsleep
import time

def main():
    reason = deepsleep.powmanGetWakeupReason()  # before init!

    if reason == 0:
        print("fresh boot")
    elif reason & deepsleep.WAKEUP_ALARM:
        print("woke from timer alarm")
    elif reason & (deepsleep.WAKEUP_GPIO0 | deepsleep.WAKEUP_GPIO1 |
                   deepsleep.WAKEUP_GPIO2 | deepsleep.WAKEUP_GPIO3):
        print("woke from GPIO")

    deepsleep.powmanInit(1704067200)
    deepsleep.powmanOffForMs(5000)

main()
```

In `main.py` there is a minimal example`.

Power consumption over one minute.


## Results

![](img/all_cycle.png)


The consumption during low power mode

![](img/low_power_mode.png)



## How It Works

Powman directly accesses memory-mapped registers to control:

* System timer
* Alarm registers
* Power regulator
* Boot configuration
* Interrupt enable flags

The library uses `mem32` internally to read and write hardware registers.

This is required for bare-metal development and is safe in this context.

---

## API Reference

### `powmanGetWakeupReason() → int`

Returns the reason for the last wake-up as a bitmask. Must be called **before** `powmanInit()`.

| Constant | Value | Meaning |
|---|---|---|
| `0` | `0x00` | Fresh boot / software reset |
| `WAKEUP_CHIP_RESET` | `0x01` | Chip-level reset |
| `WAKEUP_GPIO0` | `0x02` | Wake from PWRUP0 (used by `powmanOffUntilGPIO`) |
| `WAKEUP_GPIO1` | `0x04` | Wake from PWRUP1 |
| `WAKEUP_GPIO2` | `0x08` | Wake from PWRUP2 |
| `WAKEUP_GPIO3` | `0x10` | Wake from PWRUP3 |
| `WAKEUP_ALARM` | `0x40` | Wake from timer alarm |

The register is a bitmask: multiple bits can be set simultaneously. Use `&` to test individual sources.

Internally reads `CHIP_RESET.HAD_SWCORE_PD` (bit 25) to confirm a POWMAN sleep occurred, then reads `LAST_SWCORE_PWRUP` (offset `0xA0`) for the source.

---

### `powmanInit(absTimeMs: int)`

Initializes the POWMAN timer with an absolute timestamp in milliseconds (must be > 0).

---

### `powmanOffForMs(sleepingMs: int)`

Enters deep sleep and reboots after `sleepingMs` milliseconds. Never returns.

---

### `powmanOffUntilGPIO(gpio: int, high: bool = True)`

Enters deep sleep and reboots when the specified GPIO pin reaches the target level. `gpio` must be 0–49. Never returns.

| Parameter | Description |
|---|---|
| `gpio` | GPIO pin number (0–49) |
| `high` | `True` = wake on HIGH, `False` = wake on LOW |

> **Important:** The GPIO must already be at the **opposite** level before calling this function.
> POWMAN requires a level **transition** to fire — if the GPIO is already at the wake level when sleep is entered, the chip will never wake.
>
> | `high` | GPIO must be before sleep | Wake trigger |
> |---|---|---|
> | `True` | LOW | GPIO goes HIGH |
> | `False` | HIGH | GPIO goes LOW |

---

## Completed

- Timer-based deep sleep (`powmanOffForMs`)
- GPIO wake-up (`powmanOffUntilGPIO`)
- Wake-up reason detection (`powmanGetWakeupReason`)

## Future Developments

- Optimize power management by disabling unnecessary components
- Implement a sleep mode that does not reboot the system and preserves the values of variables like `machine.lightsleep()`
## Safety Notes

* Only use in embedded/bare-metal environments.
* Incorrect register values may brick your device.


## Supported Platforms

Tested primarily on:

* Raspberry Pi Pico 2
