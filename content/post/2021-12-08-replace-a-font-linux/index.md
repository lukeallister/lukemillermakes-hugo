---
title: "Globally replace a font in linux"
date: 2021-12-08T21:17:43.000Z
categories: 
  - "how-to"
  - "linux"
  - "tech"
tags: 
  - "font"
  - "how-to"
  - "linux"
  - "tech"
---

There are many good fonts, but a few are terrible.

In linux, we can force a replacement of a particularly hated font: Comic Sans

## Terminal

`sudo vim /etc/fonts/local.conf`

In this file, this will do it:

\`\`\` Comic Sans MS Ubuntu \`\`\`

## What is happening?

As always, the [Arch linux wiki has good documentation](https://wiki.archlinux.org/title/Font_configuration#Replace_or_set_default_fonts). What we are doing is matching font family name of "Comic Sans MS" with another: "Ubuntu." You could change the replacement font, but this one blends well in many debian based system.

Go nuke some papyrus next
