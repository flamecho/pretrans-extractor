import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hanayoi_extract as H

# 解析器已按「一条记录 = 一个文本框 = 一次点击」精确切分，不再需要启发式过滤；
# 仅剔除空文本记录。沉默台词框（如「…………。」）属于真实出现文本，保留。


def main():
    srcs = sys.argv[1].split(',')
    out = sys.argv[2]
    lines = []
    for f in srcs:
        ls, _ = H.parse_boxes(open(f, 'rb').read())
        lines.extend(t for t in ls if t.strip())
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('lines:', len(lines))


if __name__ == '__main__':
    main()
