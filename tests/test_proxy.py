import pytest

from phantom.proxy import load_file, parse_line


@pytest.mark.parametrize("line, proto, host, port, user", [
    ("1.2.3.4:80", "http", "1.2.3.4", 80, None),
    ("socks5://1.2.3.4:1080", "socks5", "1.2.3.4", 1080, None),
    ("socks5h://h.example:1080", "socks5", "h.example", 1080, None),
    ("socks4a://1.2.3.4:1080", "socks4", "1.2.3.4", 1080, None),
    ("1.2.3.4:8080:user:pass", "http", "1.2.3.4", 8080, "user"),
    ("user:pass@5.6.7.8:3128", "http", "5.6.7.8", 3128, "user"),
    ("https://u:p@proxy.example:443", "https", "proxy.example", 443, "u"),
])
def test_parse_valid(line, proto, host, port, user):
    p = parse_line(line)
    assert (p.protocol, p.host, p.port, p.user) == (proto, host, port, user)


@pytest.mark.parametrize("line", ["", "   ", "# comment", "garbage", "1.2.3.4", "1.2.3.4:0",
                                  "1.2.3.4:70000", "ftp://1.2.3.4:21"])
def test_parse_invalid(line):
    assert parse_line(line) is None


def test_default_protocol():
    assert parse_line("1.2.3.4:1080", "socks5").protocol == "socks5"


def test_label_masks_credentials():
    p = parse_line("socks5://secretuser:secretpass@1.2.3.4:1080")
    assert "secret" not in p.label()
    assert "secret" not in repr(p).replace("user='secretuser'", "")


def test_requests_url_quotes_credentials():
    p = parse_line("socks5://1.2.3.4:1080")
    p.user, p.password = "us@r", "p:ss/word"
    assert p.requests_url() == "socks5h://us%40r:p%3Ass%2Fword@1.2.3.4:1080"


def test_load_file_dedup_and_invalid(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("# header\n1.2.3.4:80\n1.2.3.4:80\nbad line\nsocks5://5.6.7.8:1080\n\n")
    proxies, invalid = load_file(str(f))
    assert [p.label() for p in proxies] == ["http://1.2.3.4:80", "socks5://5.6.7.8:1080"]
    assert invalid == 1
