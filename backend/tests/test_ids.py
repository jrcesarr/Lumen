from app.shared.ids import uuid7


def test_uuid7_versao_e_ordenacao():
    ids = [uuid7() for _ in range(1000)]
    assert all(i.version == 7 for i in ids)
    # Ordenaveis pelo tempo: bom para indices (inserts sempre no fim da arvore B).
    assert [i.bytes[:6] for i in ids] == sorted(i.bytes[:6] for i in ids)
    assert len(set(ids)) == 1000
