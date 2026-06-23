---
title: "Raspberry pi: set numlock at boot"
date: 2022-02-14T16:28:30.000Z
categories: 
  - "how-to"
  - "linux"
  - "tech"
tags: 
  - "linux"
  - "making"
  - "pi"
  - "tech"
---

On my new pi laptop (to be described in a later post) it always boots to console without numlock. I would prefer numlock to be ON always.

\> Raspbian GNU/Linux 10 (buster)

Working directory /home/pi/Dev/

Script `setNumLockOn`

``` INITTY=/dev/tty[1-8] for tty in $INITTY; do setleds -D +num < $tty done ```

Service `setNumlock.service`

``` [Unit] Description = Set numlock at boot

[Service] WorkingDirectory = /home/pi/Dev ExecStart= bash -c "/home/pi/Dev/setNumlockOn"

[Install] WantedBy=multi-user.target

```

Copy service to the right location:

sudo cp setNumlock.service /etc/systemd/system/ Start it:

sudo systemctl start setNumlock.service Set to run at boot:

sudo systemctl enable setNumlock.service

Reboot and confirm that it works.
