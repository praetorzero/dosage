from re import compile

from ..helpers import _BasicScraper, bounceStarter

class xkcd(_BasicScraper):
    starter = bounceStarter('http://xkcd.com/', compile(r'<a rel="next" href="(/?\d+/?)"[^>]*>Next'))
    imageUrl = 'http://xkcd.com/c%s.html'
    imageSearch = compile(r'<img[^<]+src="(http://imgs.xkcd.com/comics/[^<>"]+)"')
    prevSearch = compile(r'<a rel="prev" href="(/?\d+/?)"[^>]*>&lt; Prev')
    help = 'Index format: n (unpadded)'

    @classmethod
    def namer(cls, imageUrl, pageUrl):
        index = int(pageUrl.rstrip('/').split('/')[-1])
        name = imageUrl.split('/')[-1].split('.')[0]
        return 'c%03d-%s' % (index, name)



class xkcdSpanish(_BasicScraper):
    latestUrl = 'http://es.xkcd.com/xkcd-es/'
    imageUrl = 'http://es.xkcd.com/xkcd-es/strips/%s/'
    imageSearch = compile(r'src="(/site_media/strips/.+?)"')
    prevSearch = compile(r'<a rel="prev" href="(http://es.xkcd.com/xkcd-es/strips/.+?)">Anterior</a>')
    help = 'Index format: stripname'