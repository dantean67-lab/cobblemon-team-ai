from engine.stats import calc_stat, valid_evs


def test_garchomp_l100_attack(data):
    base = data.species["garchomp"]["bs"][1]
    assert calc_stat("atk", base, 100, ev=252, nature="Adamant") == 394


def test_garchomp_l50_attack(data):
    base = data.species["garchomp"]["bs"][1]
    assert calc_stat("atk", base, 50, ev=252, nature="Adamant") == 200


def test_blissey_hp(data):
    base = data.species["blissey"]["bs"][0]
    assert calc_stat("hp", base, 100, ev=252) == 714


def test_ev_validation():
    assert valid_evs({"hp": 252, "atk": 252, "spe": 4})
    assert not valid_evs({"hp": 252, "atk": 252, "spe": 8})
    assert not valid_evs({"hp": 256})
