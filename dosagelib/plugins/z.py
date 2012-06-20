from re import compile

from ..helpers import _BasicScraper


class Zapiro(_BasicScraper):
    latestUrl = 'http://www.mg.co.za/zapiro/all'
    imageSearch = compile(r'<img src="(cartoons/[^"]+)"')
    prevSearch = compile(r'<a href="([^"]+)">&gt;')



class ZombieHunters(_BasicScraper):
    latestUrl = 'http://www.thezombiehunters.com/'
    imageUrl = 'http://www.thezombiehunters.com/index.php?strip_id=%s'
    imageSearch = compile(r'"(.+?strips/.+?)"')
    prevSearch = compile(r'</a><a href="(.+?)"><img id="prevcomic" ')
    help = 'Index format: n(unpadded)'