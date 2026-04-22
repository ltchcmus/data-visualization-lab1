"""Dashboard tab modules."""

from .tab_distribution_product import render_distribution_product_tab
from .tab_price_discount import render_price_discount_tab
from .tab_publisher_author import render_publisher_author_tab
from .tab_rating_policy import render_rating_policy_tab

__all__ = [
	"render_distribution_product_tab",
	"render_price_discount_tab",
	"render_publisher_author_tab",
	"render_rating_policy_tab",
]
