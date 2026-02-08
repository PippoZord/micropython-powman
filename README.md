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

### Initialize the Timer

Set the absolute system time in milliseconds:

```python
deepsleep.powmanInit(0)
```

---

### Enter Low-Power Mode for a Duration

Put the system to sleep and wake it up after a given time:

```go
deepsleep.powmanOffForMs(10000) // Sleep for 10 seconds
```

---

### Typical Example

In `main.py` there is an example that uses the Powman functions. The device blinks the internal LED and then enters low-power mode for 10 seconds.

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

##  Main Functions

### `powmanInit(absTimeMs uint64)`

Initializes the internal timer using an absolute timestamp.

---

### `powmanOffForMs(sleepingMs uint64)`

Puts the system in deep sleep mode and schedules a wake-up alarm.


## Future Developments

- Support for waking up from low-power mode via GPIO interrupts.

## Safety Notes

* Only use in embedded/bare-metal environments.
* Incorrect register values may brick your device.


## Supported Platforms

Tested primarily on:

* Raspberry Pi Pico 2
