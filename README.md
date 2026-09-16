# lizard-button
An speaker controlled by an API and button.

# Hardware Setup

TODO

# Operating System Setup

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to load Raspberry Pi OS Lite (64-bit) on an SD card.

Configure the user, location, and network connection settings as prompted.

Once configured, boot into the system and clone this repository.

# Software Setup

Clone this repository to the Raspberry Pi.

Navigate to the repository contents and modify the configurations in the following files:
- API/button configurations: `config/device.env`
- API service: `config/lizard-api.service`
- button service: `config/lizard-button.service`

When satisfied, run `config/bootstrap.sh` with `sudo`.

&nbsp;
