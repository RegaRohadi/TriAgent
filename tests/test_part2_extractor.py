from __future__ import annotations

import pytest

from part2_scraper.extractor import ExtractionError, extract, link_density, normalize
from bs4 import BeautifulSoup

ARTICLE_TEXT = (
    "Nimbus Cloud was founded in 2008 and is headquartered in Singapore. "
    "The company is a Google Cloud Premier Partner and an Oracle NetSuite 5-Star Solution Partner. "
    "It operates seven offices across three countries with more than 170 employees. "
)

SEMANTIC_PAGE = f"""
<html><head><title>About Nimbus Cloud</title></head>
<body>
  <header><h1>Site header</h1></header>
  <nav><a href="/a">Home</a><a href="/b">Products</a><a href="/c">Contact</a></nav>
  <main><article><p>{ARTICLE_TEXT * 3}</p></article></main>
  <aside><a href="/x">Related one</a><a href="/y">Related two</a></aside>
  <footer><a href="/p">Privacy</a><a href="/t">Terms</a></footer>
  <script>var tracking = {{id: 42}}; function ping() {{ return 1; }}</script>
  <style>.header {{ color: red; font-size: 14px; }}</style>
</body></html>
"""

DIV_SOUP_PAGE = f"""
<html><head><title>Legacy layout</title></head>
<body>
  <div id="site-navigation"><a href="/1">One</a><a href="/2">Two</a></div>
  <div class="content-body"><p>{ARTICLE_TEXT * 3}</p></div>
  <div class="footer-links"><a href="/3">Three</a></div>
</body></html>
"""

def test_script_and_style_contents_are_removed():
    result = extract(SEMANTIC_PAGE)
    assert "tracking" not in result.text
    assert "font-size" not in result.text

def test_navigation_and_footer_are_removed():
    result = extract(SEMANTIC_PAGE)
    for chrome in ("Home", "Products", "Privacy", "Terms", "Related one"):
        assert chrome not in result.text

def test_article_body_survives():
    result = extract(SEMANTIC_PAGE)
    assert "Google Cloud Premier Partner" in result.text
    assert "170 employees" in result.text

def test_semantic_markup_is_preferred():
    assert extract(SEMANTIC_PAGE).strategy == "semantic"

def test_density_scoring_handles_pages_without_semantic_tags():
    result = extract(DIV_SOUP_PAGE)
    assert result.strategy == "density"
    assert "Google Cloud Premier Partner" in result.text
    assert "One" not in result.text

def test_title_is_read_before_the_header_is_deleted():
    assert extract(SEMANTIC_PAGE).title == "About Nimbus Cloud"

def test_reduction_ratio_is_reported():
    result = extract(SEMANTIC_PAGE)
    assert 0 < result.reduction_ratio < 1

def test_a_noise_word_on_the_body_tag_does_not_delete_the_page():
    page = f"""<html><body class="mediawiki vector-feature-main-menu-pinned-disabled">
      <main><p>{ARTICLE_TEXT * 3}</p></main></body></html>"""

    result = extract(page)
    assert "Google Cloud Premier Partner" in result.text

def test_a_noise_word_on_a_div_still_removes_it():
    page = f"""<html><body>
      <div class="site-menu"><a href="/a">Menu link</a></div>
      <main><p>{ARTICLE_TEXT * 3}</p></main></body></html>"""

    assert "Menu link" not in extract(page).text

def test_javascript_shell_is_reported_not_silently_empty():
    shell = "<html><head><title>App</title></head><body><div id='root'></div>" + "<script>x=1;</script>" * 50 + "</body></html>"
    with pytest.raises(ExtractionError, match="JavaScript"):
        extract(shell)

def test_link_density_is_high_for_navigation():
    nav = BeautifulSoup('<nav><a href="/a">Home</a><a href="/b">About</a></nav>', "html.parser")
    assert link_density(nav) > 0.9

def test_link_density_is_low_for_prose():
    prose = BeautifulSoup(f"<div><p>{ARTICLE_TEXT}</p><a href='/x'>one link</a></div>", "html.parser")
    assert link_density(prose) < 0.2

def test_normalize_keeps_paragraph_breaks():
    assert normalize("first  line\n\n\n  second   line  ") == "first line\nsecond line"
