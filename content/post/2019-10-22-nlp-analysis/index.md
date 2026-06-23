---
title: "NLP analysis of 'Carnival Row' and 'Frankenstein'"
date: 2019-10-22T01:33:46.000Z
categories: 
  - "data-science"
  - "literature"
  - "writing"
tags: 
  - "analysis"
  - "culture"
  - "data"
  - "data-science"
  - "literature"
  - "nlp"
  - "nltk"
  - "python"
  - "tech"
---

## Context

I am enrolled in a Natural Language Processing course this quarter. I'm enjoying it a lot and decided to share some of the coursework here.

This represents an analytic comparison between the screenplay of 'Carnival Row' and the novel _Frankenstein_.

If you're interested in literature, language, or python, I hope you find this informative.

********

## Choosing the texts

I recently watched the show ‘Carnival Row’ on Amazon. This murder mystery is set in a vibrant fantasy city in the midst of industrialization. It features urban fantasy and science fiction tropes. I enjoyed the show and wondered what other stories might be similar. Specifically, I wondered how this would compare be to Mary Shelley’s _Frankenstein_. This is worth considering because _Frankenstein_ is considered one of the first science fiction novels in English. Most fantasy and science fiction works owe at least some debt to this iconic work.

Some obvious differences between the two texts arise from format and style. “A Killing on Carnival Row” is a screenplay while _Frankenstein_ is a full novel. That means that the play will have more stage direction, while the novel will contain more narrator commentary. Also, _Frankenstein_ was written in 1818 while the “Carnival Row” screenplay was written in 2005. We’ll see later how these factors change the comparison.

The text of “A Killing on Carnival Row” is available online as a PDF scan. This added significant challenge to the project. I downloaded the PDF of the screenplay and then needed to do an OCR text scan. In Linux this can be done with command-line tools: ocrmypdf --sidecar carnival-row.txt A-Killing-On-Carnival-Row.pdf out-carnival-row.pdf. The OCR scanner actually did a great job, but this is one place where the accuracy of the comparison could be compromised.

For both _Frankenstein_ and “Carnival Row” I preprocessed the text by removing introduction and afterwords text. This gives us just the stories to compare.

## Define functions and stopwords

In order to make the coding clear to read and straightforward to reuse, let us wrap several steps in functions.

First import libraries.

```
import nltk
import re
from nltk.collocations import *
from nltk.book import FreqDist
```

Then create a stopword list

```
stopwords = nltk.corpus.stopwords.words('english')
stopwords += ['chapter','cont','ext.','int.','v.']
```

We need to ignore ‘chapter’ in order to remove the _Frankenstein_ chapter titles. Likewise ‘cont’ and ‘ext’ are used within the “Carnival Row” stage directions, so these (and other stage directions) are better ignored.

We will need an alphanumeric filter, so we’ll reuse the version presented in the session.

```
def alpha_filter(w):
  # pattern to match word of non-alphabetical characters
  pattern = re.compile('^[^a-z]+$')
  if (pattern.match(w)):
    return True
  else:
    return False
```

Let’s use a modified version of the default tokenizer since we are dealing with traditional text (not tweets or social media).

```
pattern = r''' (?x)                # set flag to allow verbose regexps
        (?:[A-Z.]{2,})+        # abbreviations, e.g. U.S.A. tweaked to include capital abbreviations, eg 'UN'
        | \$?\d+(?:\.\d+)?%?   # currency and percentages, $12.40, 50%
        | \b(?:_)             # Frankenstein text has underscores beginning letter titles. This sets those to their own character
        | \w+(?:-\w+)*         # words with internal hyphens
        | \.\.\.               # ellipsis
        | [][.,;"'?():-_%#']   # separate tokens
        '''
```

It is convenient to wrap some of our steps within functions. This allows us to apply them to any number of texts for comparison and ensures that we actually do the same steps for each corpus.

## Clean text

First let’s build a clean text function. We will use this in word frequencies, though we won’t do this for bigram, since it would split phrases.

```
def cleanText(string):
    # tokenize using pattern regex
    tokens = nltk.regexp_tokenize(string,pattern)
    # make everything lower
    words = [w.lower() for w in tokens]
    #filter stopwords 
    words = [w for w in words if w not in stopwords]
    #filter alpha
    words = [w for w in words if not alpha_filter(w)]
    return(words)
```

Next let’s import the data.

```
with open('carnival-row.txt', 'r') as file:
    carnivalRow = file.read()

with open('frankenstein.txt', 'r') as file:
    frankenstein = file.read()
```

We are comparing a novel to a play. Let’s see how many tokens each has:

```
print(len(nltk.regexp_tokenize(carnivalRow,pattern)))
```

```
## 32743
```

```
print(len(nltk.regexp_tokenize(frankenstein,pattern)))
```

```
## 84444
```

```
print(84444/32743)
```

```
## 2.5789939834468436
```

So Frankenstein is about 2.5 times longer. This is a bit of a challenge when comparing texts, but we can still consider common words and phrases.

Let’s see if the cleanText() function works as expected.

```
print(cleanText(carnivalRow)[:70])
```

```
## ['killing', 'carnival', 'row', 'written', 'travis', 'beacham', 'sewer', 'tunnel', 'night', 'archway', 'end', 'alley', 'broken', 'bent', 'long', 'ago', 'crusted', 'moss', 'trickle', 'water', 'cuts', 'scream', 'within', 'laboured', 'breathing', 'rapid', 'splish', 'splash', 'footfalls', 'aisling', 'cobweb', 'beautiful', 'intense', 'bursts', 'tunnel', 'narrow', 'alley', 'body', 'petite', 'young', 'frail', 'tense', 'fear', 'back', 'sprout', 'pair', 'large', 'moth-like', 'wings', 'fragile', 'intricate', 'frayed', 'edges', 'aisling', 'cobweb', 'faerie', 'running', 'life', 'catches', 'tattered', 'skirt', 'metal', 'grating', 'stumbles', 'face', 'first', 'turns', 'panicked', 'darkness', 'distant']
```

```
print(cleanText(frankenstein)[:70])
```

```
## ['frankenstein', 'modern', 'prometheus', 'mary', 'wollstonecraft', 'godwin', 'shelley', 'contents', 'letter', 'letter', 'letter', 'letter', 'letter', 'mrs', 'saville', 'england', 'st', 'petersburgh', 'dec', 'th', 'rejoice', 'hear', 'disaster', 'accompanied', 'commencement', 'enterprise', 'regarded', 'evil', 'forebodings', 'arrived', 'yesterday', 'first', 'task', 'assure', 'dear', 'sister', 'welfare', 'increasing', 'confidence', 'success', 'undertaking', 'already', 'far', 'north', 'london', 'walk', 'streets', 'petersburgh', 'feel', 'cold', 'northern', 'breeze', 'play', 'upon', 'cheeks', 'braces', 'nerves', 'fills', 'delight', 'understand', 'feeling', 'breeze', 'travelled', 'regions', 'towards', 'advancing', 'gives', 'foretaste', 'icy', 'climes']
```

This is working as hoped. It converts the raw text into tokens using the custom tokenizer, and then makes them lowercase, removes stopwords, and drops non-alpha characters.

Let’s save the cleanText list for later use.

```
 # clean text
carnival_clean = cleanText(carnivalRow)
franken_clean = cleanText(frankenstein)
```

## Generate Word Frequency

We’ll create a function to give us word frequency for each text.

```
def wordFreq(wordlist,wordcount):
    dist = FreqDist(wordlist)
    freq = dict()
    for word, frequency in dist.most_common(wordcount):
      freq[word] = frequency
    return(freq)
```

Now we’ll run frequency distribution for both texts using the cleanText() version of each.

```
carnivalWords = wordFreq(carnival_clean,70)
frankenWords = wordFreq(franken_clean,70)
print(carnivalWords)
```

```
## {'philostrate': 600, 'vignette': 282, 'bottom': 120, 'quill': 120, 'flute': 117, 'haruspex': 110, 'back': 100, 'faerie': 100, 'mayor': 98, 'alcandre': 87, 'one': 72, 'eyes': 69, 'tourmaline': 67, 'looks': 63, 'know': 63, 'turns': 57, 'wings': 54, 'hand': 53, 'around': 52, 'blood': 49, 'like': 45, 'later': 41, 'kasmir': 41, 'get': 40, 'dark': 38, 'inspector': 38, 'stands': 38, 'door': 38, 'dame': 37, 'window': 36, 'pulls': 36, 'behind': 35, 'faeries': 35, 'face': 34, 'black': 34, 'long': 33, 'quarter': 33, 'body': 32, 'see': 32, 'police': 32, 'grabs': 31, 'city': 31, 'jack': 31, 'wall': 30, 'right': 30, 'head': 30, 'slowly': 30, 'open': 29, 'room': 29, 'street': 28, 'think': 28, 'night': 27, 'two': 27, 'still': 27, 'something': 27, 'go': 27, 'train': 26, 'away': 26, 'young': 25, 'human': 25, 'would': 25, 'end': 24, 'takes': 24, 'sits': 24, 'stops': 24, 'magistrate': 24, 'front': 23, 'unseelie': 23, 'going': 23, 'reaches': 23}
```

```
print(frankenWords)
```

```
## {'one': 206, 'could': 197, 'would': 183, 'yet': 152, 'man': 136, 'father': 134, 'upon': 126, 'life': 115, 'every': 109, 'first': 108, 'might': 108, 'shall': 104, 'eyes': 104, 'said': 102, 'may': 99, 'time': 98, 'towards': 94, 'even': 94, 'saw': 94, 'elizabeth': 92, 'night': 88, 'found': 87, 'mind': 85, 'day': 82, 'ever': 80, 'felt': 79, 'death': 77, 'heart': 76, 'feelings': 76, 'thought': 74, 'dear': 72, 'soon': 71, 'friend': 71, 'made': 70, 'many': 68, 'still': 68, 'passed': 67, 'never': 66, 'also': 66, 'thus': 65, 'miserable': 65, 'must': 64, 'heard': 62, 'became': 61, 'like': 61, 'sometimes': 60, 'us': 60, 'love': 59, 'place': 59, 'clerval': 59, 'little': 58, 'human': 58, 'appeared': 57, 'indeed': 56, 'often': 55, 'justine': 55, 'misery': 54, 'words': 54, 'friends': 54, 'country': 53, 'nature': 53, 'although': 53, 'several': 51, 'among': 51, 'cottage': 51, 'feel': 50, 'whose': 50, 'great': 50, 'see': 50, 'old': 50}
```

These are the most common words by frequency within the two texts. Let’s also consider the words that show up in both:

```
intersects = []
for i in carnivalWords.keys():
  if i in frankenWords.keys():
    intersects.append(i)
print(intersects)
```

```
## ['one', 'eyes', 'like', 'see', 'night', 'still', 'human', 'would']
```

There are both similarities and differences in these word lists. Both have words that, while not exactly stopwords, aren’t very interesting. For example ‘back’, and ‘around’ are high scoring words in ‘Carnival Row’ that don’t tell us much. But there are a lot more filler words in _Frankenstein_: ‘could’, ‘would’, ‘upon’, and ‘among’. One thing that this tells us in comparing these texts is that the novel has more filler words. This makes sense and is what we’d expect.

Names of characters place highly in both texts. In ‘Carnival Row’ we see a bunch of names, like ‘philostrade’,‘vignette’, ‘tourmaline’, and ‘alcandre’. In Frankenstein we see names like ‘elizabeth’,‘clerval’, and ‘justine’. Names appear more often in ‘Carnival Row’ than in _Frankenstein_, mainly because they are used within the script to show who is doing what. Within _Frankenstein_ names are usually used when characters are addressing each other.

An interesting selection of words are those that are dealing with age and _kind_ or _station_ of person. In ‘Carnival Row’ we see the kinds of people represented in this story: ‘faerie’,‘human’,‘young’,‘police’, and ‘mayor’. These are associated with characterization in the story. In _Frankenstein_ we see ‘human’ in the top 70 words, though we _don’t_ see ‘creature’–that occurs in the top 100. But we have more identifiers of age and station: ‘man’,‘father’,‘friend’, and ‘old’.

Both stories contain words connoting violence and horror. ‘Carnival Row’ includes various body parts like ‘eyes’,‘wings’,‘hand’,‘face’,‘body’, and ‘head’. Other words that give the sense of the setting are ‘blood’,‘dark’,‘door’,‘behind’,‘black’,‘slowly’, and ‘night’. Together, these common words would probably tell us that this was a murder mystery, even if we never read the text. _Frankenstein_ is much more balanced in tone, though it still presents words that connote horror. We again have ‘eyes’, and ‘night’ but we also have ‘death’, ‘passed’, ‘misery’, miserable’, and ‘old’

Unlike ‘Carnival Row’, _Frankenstein_ contains many emotion words. We see ‘felt’, ‘heart’, ‘feelings’, and ‘love’. Does that mean that ‘Carnival Row’ is unconcerned with these things? Definitely not. Rather, this is a structural difference. _Frankenstein_ relies on the structure of nested letters and narratives. The perception of the narrator plays an important part of the story. On the flip side, “Carnival Row” is a screenplay and as such relies on setting and the actors to portray most of the emotion. That is, where _Frankenstein_ will _tell_ the reader that the creature is miserable, “Carnival Row” will rely on the actors’ portrayal of the emotions. So even though both stories contain similar emotions, they are more easily seen in the text of _Frankenstein_.

## Generate Bigrams

Next let’s create bigram functions so we can likewise apply them to the texts.

```
def freqBigrams(string):
    # tokenize using pattern regex
    tokens = nltk.regexp_tokenize(string,pattern)
    # make everything lower
    wordlist = [w.lower() for w in tokens]
    #create measures object
    bigram_measures = nltk.collocations.BigramAssocMeasures() 
    #create finder
    finder = BigramCollocationFinder.from_words(wordlist) 
    # remove non-alphas
    finder.apply_word_filter(alpha_filter)
    # remove stopwords
    finder.apply_word_filter(lambda w: w in stopwords)
    # get bigrams by raw frequency
    scored = finder.score_ngrams(bigram_measures.raw_freq)
    return(scored)

def PMIBigrams(string):
    # tokenize using pattern regex
    tokens = nltk.regexp_tokenize(string,pattern)
    # make everything lower
    wordlist = [w.lower() for w in tokens]
    #create measures object
    #create measures object
    bigram_measures = nltk.collocations.BigramAssocMeasures() 
    #create finder
    finder = BigramCollocationFinder.from_words(wordlist) 
    # remove non-alphas
    finder.apply_word_filter(alpha_filter)
    # remove stopwords
    finder.apply_word_filter(lambda w: w in stopwords)
    # remove low frequency
    finder.apply_freq_filter(5)
    # get bigrams PMI
    scored = finder.score_ngrams(bigram_measures.pmi)
    return(scored)
```

The PMI uses a frequency filter of 5 to ensure that the words that show up are actually common to the texts.

Now that we have those we can apply them to the texts.

```
# generate frequency bigrams
carnivalFreqBigrams = freqBigrams(carnivalRow)
frankenFreqBigrams = freqBigrams(frankenstein)

# generate PMI bigrams
carnivalPMIBigrams = PMIBigrams(carnivalRow)
frankenPMIBigrams = PMIBigrams(frankenstein)
```

All that’s left is to compare them.

## Bigram analysis

### Frequency bigrams

```
for i in carnivalFreqBigrams[:50]:
    print(i)
```

```
## (('unseelie', 'jack'), 0.0006108175793299331)
## (('moments', 'later'), 0.0005802767003634364)
## (('faerie', 'blood'), 0.0005191949424304431)
## (('faerie', 'quarter'), 0.0004581131844974498)
## (('later', 'philostrate'), 0.0004581131844974498)
## (('philostrate', 'looks'), 0.0003664905475979599)
## (('carnival', 'row'), 0.00033594966863146323)
## (('sergeant', 'bottom'), 0.00033594966863146323)
## (('young', 'girl'), 0.00033594966863146323)
## (('magistrate', 'flute'), 0.00030540878966496657)
## (('dark', 'figure'), 0.0002748679106984699)
## (('madame', 'mab'), 0.0002748679106984699)
## (('philostrate', 'stands'), 0.00024432703173197324)
## (('philostrate', 'turns'), 0.00024432703173197324)
## (('screaming', 'banshee'), 0.00024432703173197324)
## (('argyle', 'heights'), 0.00021378615276547658)
## (('looks', 'around'), 0.00021378615276547658)
## (('police', 'carriage'), 0.00021378615276547658)
## (('bloody', 'hell'), 0.00018324527379897995)
## (('continuous', 'philostrate'), 0.00018324527379897995)
## (('dame', 'whitley'), 0.00018324527379897995)
## (('guinevere', 'cartier'), 0.00018324527379897995)
## (('metropolitan', 'constabulary'), 0.00018324527379897995)
## (('natural', 'history'), 0.00018324527379897995)
## (('philostrate', 'grabs'), 0.00018324527379897995)
## (('philostrate', 'walks'), 0.00018324527379897995)
## (('vignette', 'looks'), 0.00018324527379897995)
## (('aisling', 'cobweb'), 0.00015270439483248328)
## (('banshee', 'printing'), 0.00015270439483248328)
## (('bleakness', 'keep'), 0.00015270439483248328)
## (('brass', 'horn'), 0.00015270439483248328)
## (('chambre', 'de'), 0.00015270439483248328)
## (('dalrymple', 'street'), 0.00015270439483248328)
## (('de', 'madame'), 0.00015270439483248328)
## (('faerie', 'mother'), 0.00015270439483248328)
## (('faerie', 'wings'), 0.00015270439483248328)
## (('hand', 'grabs'), 0.00015270439483248328)
## (('le', 'chambre'), 0.00015270439483248328)
## (('philostrate', 'pulls'), 0.00015270439483248328)
## (('philostrate', 'runs'), 0.00015270439483248328)
## (('philostrate', 'stops'), 0.00015270439483248328)
## (('philostrate', 'vignette'), 0.00015270439483248328)
## (('printing', 'office'), 0.00015270439483248328)
## (('royal', 'museum'), 0.00015270439483248328)
## (('underground', 'station'), 0.00015270439483248328)
## (('backs', 'away'), 0.00012216351586598662)
## (('begin', 'montage'), 0.00012216351586598662)
## (('eyes', 'meet'), 0.00012216351586598662)
## (('gatling', 'gun'), 0.00012216351586598662)
## (('inspector', 'philostrate'), 0.00012216351586598662)
```

```
for i in frankenFreqBigrams[:50]:
    print(i)
```

```
## (('old', 'man'), 0.00040263369807209514)
## (('native', 'country'), 0.00017763251385533607)
## (('natural', 'philosophy'), 0.00016579034626498034)
## (('taken', 'place'), 0.0001539481786746246)
## (('fellow', 'creatures'), 0.00013026384349391313)
## (('dear', 'victor'), 0.00011842167590355739)
## (('looked', 'upon'), 0.00011842167590355739)
## (('de', 'lacey'), 0.00010657950831320165)
## (('m.', 'waldman'), 0.00010657950831320165)
## (('nothing', 'could'), 0.00010657950831320165)
## (('one', 'another'), 0.00010657950831320165)
## (('young', 'man'), 0.00010657950831320165)
## (('every', 'day'), 9.47373407228459e-05)
## (('first', 'time'), 9.47373407228459e-05)
## (('long', 'time'), 9.47373407228459e-05)
## (('m.', 'krempe'), 9.47373407228459e-05)
## (('many', 'months'), 9.47373407228459e-05)
## (('mont', 'blanc'), 9.47373407228459e-05)
## (('one', 'day'), 9.47373407228459e-05)
## (('poor', 'girl'), 9.47373407228459e-05)
## (('several', 'hours'), 9.47373407228459e-05)
## (('human', 'beings'), 8.289517313249017e-05)
## (('many', 'hours'), 8.289517313249017e-05)
## (('passed', 'away'), 8.289517313249017e-05)
## (('short', 'time'), 8.289517313249017e-05)
## (('take', 'place'), 8.289517313249017e-05)
## (('two', 'months'), 8.289517313249017e-05)
## (('two', 'years'), 8.289517313249017e-05)
## (('cornelius', 'agrippa'), 7.105300554213443e-05)
## (('first', 'saw'), 7.105300554213443e-05)
## (('native', 'town'), 7.105300554213443e-05)
## (('nearly', 'two'), 7.105300554213443e-05)
## (('next', 'morning'), 7.105300554213443e-05)
## (('poor', 'william'), 7.105300554213443e-05)
## (('two', 'days'), 7.105300554213443e-05)
## (('cannot', 'describe'), 5.9210837951778695e-05)
## (('countenance', 'expressed'), 5.9210837951778695e-05)
## (('dear', 'sister'), 5.9210837951778695e-05)
## (('dearest', 'victor'), 5.9210837951778695e-05)
## (('died', 'away'), 5.9210837951778695e-05)
## (('ever', 'since'), 5.9210837951778695e-05)
## (('every', 'one'), 5.9210837951778695e-05)
## (('gentle', 'manners'), 5.9210837951778695e-05)
## (('great', 'god'), 5.9210837951778695e-05)
## (('many', 'years'), 5.9210837951778695e-05)
## (('never', 'saw'), 5.9210837951778695e-05)
## (('new', 'scene'), 5.9210837951778695e-05)
## (('one', 'time'), 5.9210837951778695e-05)
## (('pressed', 'upon'), 5.9210837951778695e-05)
## (('took', 'place'), 5.9210837951778695e-05)
```

For ‘Carnival Row’ this shows even more the extent of the stage directions within the script. We see ‘philostrade looks’, ‘philostrade stands’, ‘philostrade stands’, etc. all the way down. Many of these phrases are about the movement of the characters in the story.

We actually see the same thing in _Frankenstein_, but the movement is through time rather than from one scene in a set to another. We have ‘many months’, ‘every day’, ‘first time’, ‘several hours’, and many other time periods. These are here because of the structure of the narrative in Frankenstein: the story is nested within letters recounting the story in several layers. First we have Captain Walton’s letter, which includes Victor Frankenstein’s story, which includes the Creature’s story. Each of these people are telling their story in a past tense first person limited view. That means _Frankenstein_ relies on a lot of time period description. We shouldn’t be surprised to see ‘next morning’ and ‘many years’ in the top 50 frequency bigrams.

‘Carnival Row’ contains a great many person and place names within the top 50 frequency bigrams. In addition to the main character ‘philostrade’ we see places like ‘faerie quarter’, ‘bleakness keep’, and ‘dalrymple street’.

One particularly interesting bigram is ‘natural history’ in ‘Carnival Row’, which corresponds closely to _Frankenstein_’s ‘natural philosophy’. The difference in terminology arises from the few hundred years between the writing of _Frankenstein_ (1818) and ‘Carnival Row’ (2005). These terms both refer to science and the idea of scientific progress. Both stories present an uncertain look at this notion of progress, as it leads to violence and predation (‘Carnival Row’) or careless experimentation _(Frankenstein)_. In each case, unfettered science destroys people.

### Bigrams by PMI

```
for i in carnivalPMIBigrams[:50]:
    print(i)
```

```
## (('brass', 'horn'), 12.413936390220119)
## (('chambre', 'de'), 12.413936390220119)
## (('le', 'chambre'), 12.413936390220119)
## (('metropolitan', 'constabulary'), 11.998898890941273)
## (('argyle', 'heights'), 11.828973889498961)
## (('natural', 'history'), 11.776506469604826)
## (('madame', 'mab'), 11.676970796053915)
## (('banshee', 'printing'), 11.565939483665169)
## (('screaming', 'banshee'), 11.507045794611603)
## (('de', 'madame'), 11.413936390220119)
## (('royal', 'museum'), 11.413936390220119)
## (('aisling', 'cobweb'), 11.03542476696639)
## (('bleakness', 'keep'), 10.928509563049879)
## (('carnival', 'row'), 10.785905167607078)
## (('bloody', 'hell'), 10.776506469604827)
## (('printing', 'office'), 10.565939483665169)
## (('dalrymple', 'street'), 10.191543968883671)
## (('underground', 'station'), 10.054040445133737)
## (('guinevere', 'cartier'), 10.02161896744136)
## (('unseelie', 'jack'), 9.84306871938475)
## (('dame', 'whitley'), 9.789445525312324)
## (('young', 'girl'), 9.566546806360263)
## (('moments', 'later'), 9.496956976988018)
## (('police', 'carriage'), 8.806253812998879)
## (('dark', 'figure'), 8.461464760302706)
## (('faerie', 'mother'), 7.355042701166552)
## (('faerie', 'quarter'), 7.217539177416615)
## (('sergeant', 'bottom'), 7.159122491191294)
## (('magistrate', 'flute'), 6.865499765524078)
## (('faerie', 'blood'), 6.827795698301681)
## (('hand', 'grabs'), 6.638710220878565)
## (('looks', 'around'), 6.1285341713578685)
## (('faerie', 'wings'), 4.922083293890443)
## (('philostrate', 'walks'), 4.895611082529252)
## (('philostrate', 'runs'), 4.632576676695459)
## (('later', 'philostrate'), 4.3194187914358295)
## (('continuous', 'philostrate'), 3.8956110825292516)
## (('philostrate', 'stands'), 3.5221526870018103)
## (('philostrate', 'stops'), 3.507045794611601)
## (('vignette', 'looks'), 3.4670301157637216)
## (('philostrate', 'grabs'), 3.400846390779673)
## (('philostrate', 'looks'), 3.377762777666632)
## (('philostrate', 'turns'), 2.937190186280654)
## (('philostrate', 'pulls'), 2.9220832938904433)
## (('philostrate', 'vignette'), -0.047543057066036454)
```

```
for i in frankenPMIBigrams[:50]:
    print(i)
```

```
## (('cornelius', 'agrippa'), 13.365707298398945)
## (('de', 'lacey'), 13.043779203511587)
## (('mont', 'blanc'), 12.780744797677793)
## (('m.', 'waldman'), 11.842145342341936)
## (('natural', 'philosophy'), 11.681209124126875)
## (('m.', 'krempe'), 11.672220340899624)
## (('fellow', 'creatures'), 10.432821494257485)
## (('next', 'morning'), 9.964827862116762)
## (('native', 'country'), 9.73732251738666)
## (('dearest', 'victor'), 9.71035546978639)
## (('native', 'town'), 9.442875158921407)
## (('gentle', 'manners'), 9.352245038592383)
## (('young', 'woman'), 9.32131317904049)
## (('cannot', 'describe'), 9.257182841620775)
## (('taken', 'place'), 9.139109847819745)
## (('poor', 'girl'), 9.06649928001167)
## (('human', 'beings'), 8.855649606691681)
## (('nearly', 'two'), 8.844761290548945)
## (('take', 'place'), 8.830987552457412)
## (('poor', 'william'), 8.814960513015704)
## (('old', 'man'), 8.72185110862422)
## (('dear', 'victor'), 8.71035546978639)
## (('countenance', 'expressed'), 8.701793456282966)
## (('two', 'months'), 8.639732488150717)
## (('several', 'hours'), 8.605819115177114)
## (('great', 'god'), 8.584347584874285)
## (('short', 'time'), 8.470889535091004)
## (('two', 'years'), 8.465703088375667)
## (('died', 'away'), 8.399923013736858)
## (('pressed', 'upon'), 8.388427374899027)
## (('two', 'days'), 8.14815343399888)
## (('many', 'hours'), 7.998136537955871)
## (('many', 'months'), 7.992842238286361)
## (('new', 'scene'), 7.94280155578676)
## (('looked', 'upon'), 7.852374474658818)
## (('dear', 'sister'), 7.762822889680525)
## (('took', 'place'), 7.635067342482152)
## (('ever', 'since'), 7.610819796235477)
## (('young', 'man'), 7.541278862982402)
## (('passed', 'away'), 7.463116840224055)
## (('long', 'time'), 7.227435498226727)
## (('many', 'years'), 7.1407409333986696)
## (('nothing', 'could'), 6.628178261522637)
## (('one', 'another'), 6.2945429209804065)
## (('every', 'day'), 6.239970969003936)
## (('never', 'saw'), 6.088652422250215)
## (('first', 'time'), 5.996109952120271)
## (('first', 'saw'), 5.641193445278997)
## (('one', 'day'), 5.321654766597646)
## (('one', 'time'), 4.386425021987879)
```

The Mutual Information scores look very similar to the frequency bigrams, though there are some useful changes. One very helpful difference is the way that it moves the stage directions lower. In ‘Carnival Row’ the terms ‘philostrade stands’, ‘philostrade stops’, etc. are now lower because they occur so often. We now see phrases that show the tone of both texts are similar than the simple word frequency score would indicate.

‘Carnival Row’ still has phrases and terms that indicate violence and horror, (e.g. ‘screaming banshee’, ‘dark figure’, and ‘hand grabs’) but we can now see similar terms over in _Frankenstein_. For example, we now see ‘poor girl’ and ‘great god’–an expression of horror that closely parallels the ‘bloody hell’ that we see over in ‘Carnival Row’.

An important similarity that the PMI scores show is the relation of ‘young girl’ in ‘Carnival Row’ with the ‘young woman’ and ‘poor girl’ in the _Frankenstein_ side. The explanation for this particular relationship relies on knowledge of the texts. In both stories these terms refer to the victims of the violence. One explanation for the similarity in tone, horror, and violence within these two stories is that an innocent always suffers for the sins of others.

## Conclusions about the texts

These texts are very different in structure and presentation. Yet they present very similar themes, tones, and story. Though they were separated by almost 200 years, they employ similar words and themes to explore the danger of unbridled scientific progress. Though it’s impossible to say for certain that ‘Carnival Row’ was influenced by _Frankenstein_, the similarity within the texts indicates that this assumption is not far-fetched. At the very least they express similar concerns and genres of storytelling–despite the fact that the formatting and structure is totally different.

## Challenges and technical notes

The challenges of comparing these texts are numerous. The most obvious challenge is the structural difference between a screenplay and a novel. The number of words in each is different. The stage direction and descriptive elements are different. Another issue is that of historical time and language usage. These were written almost 200 years apart so common phrases and syntactical style have greatly changed since then.

Technical challenges include the data collection. The ‘Carnival Row’ screenplay was available only as a pdf so I had to convert it to text. On the other end of the spectrum, _Frankenstein_ is an easy text to obtain, since it’s available from Gutenberg.

Ultimately this was an interesting puzzle that begins to show the kind of literary analysis that can be assisted by NLP processing.
