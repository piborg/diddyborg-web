# diddyborg-web
Web based interface for controlling DiddyBorg from a phone or browser.
![](screenshot.png?raw=true)

This example provides web-based access to a DiddyBorg or DiddyBorg Metal Edition using a web browser on both phones and desktops.
The interface streams images from the Raspberry Pi camera, movement can be controlled from the buttons.

Additionally the current image may be saved to the SD card with a button press.

It is intended for use with:
* [DiddyBorg Metal Edition](https://www.piborg.org/diddyborg/metaledition)
* [DiddyBorg Red Edition](https://www.piborg.org/diddyborg/rededition)
* [DiddyBorg](https://www.piborg.org/diddyborg)
* [4Borg](https://www.piborg.org/4Borg)
* [YetiBorg](https://www.piborg.org/yetiborg)

## Getting ready
Before using this script you should make sure your DiddyBorg is working with the standard examples.

You will need to also perform the optional camera setup so the script can stream images.
You will not need the option joystick setup for this example.

You will probably want to use a WiFi dongle for the best results.
Make sure your WiFi is working and connected to you router before running the scripts.

* [DiddyBorg Metal Edition setup instructions](https://www.piborg.org/diddyborg/metaledition/install)
* [DiddyBorg Red Edition setup instructions](https://www.piborg.org/diddyborg/rededition/install)
* [DiddyBorg setup instructions](https://www.piborg.org/diddyborg/install)
* [4Borg setup instructions](https://www.piborg.org/4Borg/install)
* [YetiBorg setup instructions](https://www.piborg.org/yetiborg/install)

## Downloading the code
To get the code we will clone this repository to the Raspberry Pi.
In a terminal run the following commands
```bash
cd ~
git clone https://github.com/piborg/diddyborg-web.git
```

## Running the code
This is easiest done via SSH over the WiFi.

First find out what your IP address is using the `ifconfig` command.
It should be 4 numbers separated by dots, e.g. `192.168.0.198`
We will need this to access the controls, so make a note of it.

Next run the script for your robot:
* DiddyBorg Metal Edition → `sudo ~/diddyborg-web/metalWeb.py`
* DiddyBorg Red Edition → `sudo ~/diddyborg-web/diddyRedWeb.py`
* DiddyBorg → `sudo ~/diddyborg-web/diddyWeb.py`
* 4Borg → `sudo ~/diddyborg-web/4BorgWeb.py`
* YetiBorg → `sudo ~/diddyborg-web/yetiWeb.py`

Wait for the script to load, when it is ready it should say:
`Press CTRL+C to terminate the web-server`

## Controlling your robot
Load your web browser on your phone or desktop.
Once loaded enter your IP address in the address bar

You should be presented with the camera image, some text, some buttons, and a slider.
![](screenshot.png?raw=true)

To move click a movement button, such as **Forward**.
To stop moving click the **Stop** button.

To change the speed, drag the slider before clicking a movement button.
Left is slower, right is faster.

The last motor settings are displayed below the image.

## Alternative options
There are some other URLs you can use to get different functionality.
Replace `192.168.0.198` in the below addresses with your IP address:
* http://192.168.0.198 - Standard controls, click to change speed
* http://192.168.0.198/hold - Press and hold controls, may not work on all devices
* http://192.168.0.198/stream - Gets the video stream without any controls
* http://192.168.0.198/cam.jpg - Single frame from the camera, you may need to force-refresh to get a new image

## Additional settings
There are some settings towards the top of the script which may be changed to adjust the behaviour of the interface:
* `webPort` - Sets the port number, 80 is the default port web browsers will try
* `imageWidth` - The width of the captured camera image, higher will need more network bandwidth
* `imageHeight` - The height of the captured camera image, higher will need more network bandwidth
* `frameRate` - The number of images taken from the camera each second by the Raspberry Pi
* `displayRate` - The number of times per second the web browser will refresh the camera image
* `photoDirectory` - The directory that photos are saved to when taken

## Auto start at boot
To get the web interface to load on its own do the following:

1. Open the Cron table using `crontab -e`
2. Add a cron job to the bottom of the file using one of the following lines:
  * DiddyBorg Metal Edition → `@reboot sudo /home/pi/diddyborg-web/metalWeb.py`
  * DiddyBorg Red Edition → `@reboot sudo /home/pi/diddyborg-web/diddyRedWeb.py`
  * DiddyBorg → `@reboot sudo /home/pi/diddyborg-web/diddyWeb.py`
  * 4Borg → `@reboot sudo /home/pi/diddyborg-web/4BorgWeb.py`
  * 4Borg → `@reboot sudo /home/pi/diddyborg-web/yetiWeb.py`
3. Save the file
4. Close the file

The cron table should now auto-run the script when the Raspberry Pi boots up.

## Going further
This is just a simple example of how a web interface can be made using Python on the Raspberry Pi to control a robot.

We think sharing software is awesome, so we encourage others to extend and/or improve on this script to make it do even more :)
