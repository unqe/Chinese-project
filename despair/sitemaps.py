from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from menu.models import MenuItem


class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return ["home", "menu:menu", "terms", "privacy"]

    def location(self, item):
        return reverse(item)


class MenuItemSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return MenuItem.objects.filter(is_available=True).order_by("pk")

    def location(self, item):
        return reverse("menu:item_detail", args=[item.pk])

    def lastmod(self, item):
        return None


sitemaps = {
    "static": StaticViewSitemap,
    "menu": MenuItemSitemap,
}
