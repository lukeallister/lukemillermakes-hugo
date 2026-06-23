---
title: "How to Fix the \"Media change\" error on a Debian-based system"
date: 2017-12-20T19:28:19.000Z
categories: 
  - "how-to"
  - "linux"
  - "server"
---

Today I ran into a strange error when I attempted to install a package on a debian server. When I tried to run `apt-get install` I encountered this error:

```
Media change: please insert the disc labeled
 'Debian GNU/Linux 9.3.0 _Stretch_ - Official amd64 xfce-CD Binary-1 20171209-12:11'
in the drive '/media/cdrom/' and press [Enter]

```

Essentially what this is saying is that it expects to install software from a cd _that is not in the cd drive_. That is problematic. We want to install new programs from the debian repository, as well as updates.

The fix was to edit the source list located at `/etc/apt/sources.list`. For me there was a line that said

```
deb cdrom:[Debian GNU/Linux 9.3.0 _Stretch_ - Official amd64 xfce-CD Binary-1 20171209-12:11]/ stretch main
```

that must have been enabled when setting up the server from CD. All I had to do was to comment it out by putting a `#` sign at the beginning of the line.

Then when I again ran `apt-get install` the system knew to grab the package from the appropriate repository. Crisis averted.
