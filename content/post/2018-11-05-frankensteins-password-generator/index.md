---
title: "Frankenstein's password generator"
date: 2018-11-05T22:52:12.000Z
categories: 
  - "culture"
  - "tech"
tags: 
  - "cryptography"
  - "frankenstein"
  - "games"
  - "hacks"
  - "library"
  - "literature"
  - "making"
  - "nerd"
  - "passwords"
  - "tech"
---

Do you remember this xkcd password comic?

![To anyone who understands information theory and security and is in an infuriating argument with someone who does not (possibly involving mixed case), I sincerely apologize.](images/password_strength.png)

Well I love it. This is such a good idea that I wrote a script to do this.

****** **Disclaimer**: I am no security expert; I am just a nerd. Do your own research and make your own decisions. This info is provided for entertainment only. If you choose a bad password and awaken to see silly things posted on your facebook account, that is your fault and your problem. It is my opinion that strong passwords that you can remember are better than weak passwords that you can't. And password managers are better than trying remembering passwords in the first place. ******

I read from the Project Gutenberg [Frankenstein](https://www.gutenberg.org/ebooks/84) and created a spin-off password generator.

Many sites have minimum password requirements, so I made some changes to make this easy to fulfill.

- I added random capitalization. This fulfills the "must include capital letters" requirement of many sites - I added a number - I added punctuation

And here it is, running and randomly generating each time you refresh this page: <!-- dynamic content (pass) was hosted by a WordPress plugin and is no longer available -->

Now let's talk about entropy. According to a very informative post on [stackoverflow](https://crypto.stackexchange.com/a/376), I have a back-of the envelope way to calclulate entropy. Am I doing it right? I don't know.

If you know about this, leave a comment.

_Frankenstein_ has 4758 words. - This means one word chosen at random has an entropy of `log2(4758) = 12.22 bits of entropy ` - By randomly capitalizing each word, we double the effective number of words: `log2(4758*2) = 13.22 bits ` - By stringing the words together, we get ` log2(4758*2)*3 = 39.65 bits ` -Then we add a random digit 0-9: ` log2(4758*2)*3+log2(10) = 42.97 bits `

So this is really good, but it's not as good as it could be. If we want something better, we could choose another couple texts with similar language. That's what I'm going to do (but I'm not going to tell you which ones).

So here's an updated version: <!-- dynamic content (pass2) was hosted by a WordPress plugin and is no longer available -->

Now if you want this to become even better, you could modify this to: - use a system dictionary instead of a text (49.06 bits of entropy) - add 2 digits at the end instead of 3 (49.40 bits) - use 4 words instead of 3 (60.33 bits) - Do all of them (67.63 bits)

Or you could take a totally different approach. Instead of trying to remember and type passwords, use a password manager and pseudo-random alphanumeric characters.

for example, the code

```
echo `date` | sha256sum | head -c16 

```

produces: <!-- dynamic content (pass3) was hosted by a WordPress plugin and is no longer available -->

There are 36 options here [a-z][0-9], so 16 digits of that gives an entropy of 82.72 bits.

How do you choose your passwords? If you need a new one, feel free to bookmark this page and come back. If I'm doing it wrong, please let me know in the comments below.

Thanks for reading!
