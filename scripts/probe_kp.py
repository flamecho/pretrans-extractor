# Known-plaintext recovery analysis for Akaru_route1.spt
# For each (corrupted source hex, known clean plaintext), compare byte-by-byte.
import binascii

data = {
 "m2_っラン": ("82c183898393836a8393834f83458346834182c9928591d682a682c48141919682e98f8094f582f082b782e98142",
              "ランニングウェアに着替えて、走る準備をする。"),
 "m3_C付#名": ("4395742396bc0d0a817582e6815b82b58141919682e982bc81498176",
              "#名\r\n「よーし、走るぞ！」"),
 "m4_て走る": ("82c4919682e98142",
              "走る。"),
 "m7_獅ｵばら": ("8e82b582ce82ad919682ea82c882a982c182bd95aa814182a282c282e082e682e88b9797a382f0904c82ce82b582c40d0a919682e9814296b3905382c9919682ea82e982cc82aa8af082b582a982c182bd8142",
              "獅ばらく走れなかった分、いつもより距離を伸ばして\r\n走る。無心に走れるのが嬉しかった。"),
 "m8_oし#名": ("6f82b52396bc0d0a817582f18163816381488176",
              "#名\r\n「ん……？」"),
 "m10_c＠s": ("638197730d0a817582a882a4814182a882cd82e682a4814283898393834a8393834f928682a98176",
              "「おう、おはよう。ランニング中か」"),
}

for name,(hx,plain) in data.items():
    corr = binascii.unhexlify(hx)
    try:
        real = plain.encode("cp932")
    except Exception as e:
        print(name,"ENCODE ERR",e); continue
    print(f"\n=== {name} ===")
    print(f"  corr_len={len(corr)} real_len={len(real)}")
    n=max(len(corr),len(real))
    for i in range(n):
        c = corr[i] if i<len(corr) else None
        r = real[i] if i<len(real) else None
        if c is None or r is None:
            print(f"  [{i:2}] corr={c!r} real={r!r}  {'<' if (c!=r) else '='}")
        else:
            x = c^r
            mark = "==" if c==r else f"XOR={x:02X}"
            print(f"  [{i:2}] corr={c:02X} real={r:02X} {mark}")
