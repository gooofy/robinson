# robinson
Tiny pyhton (cython) HTML layout engine with cairo surface rendering support


tiny html+css renderer, based on mbrubeck's rendering engine 

http://limpet.net/mbrubeck/2014/08/08/toy-layout-engine-1.html

with some enhancements:

- uses lxml + tinycss for parsing
- uses cssselect for css selector handling
- some support for inline and table layout
- support for text and fonts including word wrapping and alignment

two sample images of what it can do (rendered from the test/ folder):

![weather](https://raw.githubusercontent.com/gooofy/robinson/master/weather.png)

![splash screen](https://raw.githubusercontent.com/gooofy/robinson/master/splash.png)

