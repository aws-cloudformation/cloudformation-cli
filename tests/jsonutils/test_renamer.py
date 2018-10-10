from uluru.jsonutils.renamer import RefRenamer


def test_banned_renames():
    rr1 = RefRenamer()
    default = next(rr1.names)
    rr2 = RefRenamer(banned={default})
    assert next(rr2.names) != default
