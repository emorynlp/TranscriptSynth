# ========================================================================
# Copyright 2023 Emory University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========================================================================

__author__ = 'Jinho D. Choi'

import json
import os.path
from typing import Optional

from align4d import align
from elit_tokenizer import EnglishTokenizer

DEFAULT_SPEAKER = '0'


def whisper_transcript(filepath: str, tokenizer: EnglishTokenizer) -> tuple[list[str], list[int]]:
    transcript = json.load(open(filepath))
    text = ' '.join([u for u in transcript])

    tokens, sids = [], []
    for sid, s in enumerate(tokenizer.decode(text, segment=2)):
        t = text[s.offsets[0][0]:s.offsets[-1][1]].split()
        tokens.extend(t)
        sids.extend([sid] * len(t))

    return tokens, sids


def target_transcript(filepath: str) -> tuple[list[list[str]], list[str]]:
    transcript = json.load(open(filepath))
    utterances, speakers = [], []

    for utterance in transcript:
        t = utterance[1].split()
        speakers.append(utterance[0])
        # utterances.append([DEFAULT_SPEAKER_ID, t])  # TODO: after updated
        utterances.append([DEFAULT_SPEAKER, ' '.join(t)])

    return utterances, speakers


def align4d_to_whisper(w_tokens: list[str], a_tokens: list[str]) -> dict[int, int]:
    maps, idx = dict(), 0
    for w_idx, w_token in enumerate(w_tokens):
        for a_idx in range(idx, len(a_tokens)):
            if w_token == a_tokens[a_idx]:
                maps[a_idx] = w_idx
                idx = a_idx + 1
                break
    return maps


def target_to_align4d(t_utterances: list[list[str]], a_tokens: list[str]) -> list[list[int]]:
    maps, idx = [], 0
    for utterance in t_utterances:
        indices = []
        for token in utterance:
            for i in range(idx, len(a_tokens)):
                if token == a_tokens[i]:
                    indices.append(i)
                    idx = i + 1
                    break
            else:
                indices.append(-1)
        maps.append(indices)
    return maps


def target_to_whisper(w_tokens: list[str], w_sids: list[int], t_speakers: list[str], t2a: list[list[int]], a2w: dict[int, int]) -> list[list[str]]:
    t2w, idx = [], 0

    for t_idx, t_indices in enumerate(t2a):
        sid = t_speakers[t_idx]
        cfst = next((i for i in t_indices if i >= 0 and i in a2w), -1)
        if cfst == -1:
            t2w.append([sid, None])
            continue
        plst = next(i for i in reversed(t_indices) if i >= 0 and i in a2w)
        cfst, plst = a2w[cfst], a2w[plst] + 1
        if cfst > idx:
            t2w.append(['', (idx, cfst)])
        t2w.append([sid, (cfst, plst)])
        idx = plst

    while True:
        for i, curr in enumerate(t2w):
            if i == 0: continue
            prev = t2w[i - 1]
            if curr is None or prev is None or curr[1] is None or prev[1] is None: continue
            c_sid, (c_fst, c_lst) = curr[0], curr[1]
            p_sid, (p_fst, p_lst) = prev[0], prev[1]

            if w_sids[p_lst - 1] == w_sids[c_fst]:
                sid = w_sids[c_fst]
                # merge unmatched tokens to the next utterance
                if not p_sid:
                    if c_sid:
                        curr[1] = (p_fst, c_lst)
                        t2w[i - 1] = None
                # merge unmatched tokens to the previous utterance
                elif not c_sid:
                    if p_sid:
                        prev[1] = (p_fst, c_lst)
                        t2w[i] = None
                # merge partial segments
                else:
                    plst = p_fst
                    for j in range(p_lst - 2, p_fst - 1, -1):
                        if w_sids[j] != sid:
                            plst = j + 1
                            break
                    cfst = c_lst
                    for j in range(c_fst + 1, c_lst):
                        if w_sids[j] != sid:
                            cfst = j
                            break

                    if p_lst - plst < cfst - c_fst and plst - p_fst > 0:
                        prev[1] = (p_fst, plst)
                        curr[1] = (plst, c_lst)
                    else:
                        prev[1] = (p_fst, cfst)
                        curr[1] = (cfst, c_lst)

        p_len = len(t2w)
        t2w = [t for t in t2w if t is not None]
        if p_len == len(t2w): break

    for curr in t2w:
        t = curr[1]
        curr[1] = '' if t is None else ' '.join(w_tokens[t[0]:t[1]])

    return t2w


def fuse(whisper_input: str, target_input: str, fuse_output: str, tokenizer: EnglishTokenizer, align_output: Optional[str] = None) -> list[list[str]]:
    w_tokens, w_sids = whisper_transcript(whisper_input, tokenizer)
    t_utterances, t_speakers = target_transcript(target_input)

    if align_output and os.path.exists(align_output):
        a_output = json.load(open(align_output))
    else:
        a_output = align.align(w_tokens, t_utterances)
        if align_output:
            json.dump(a_output, open(align_output, 'w'))

    t_utterances = [u[1].split() for u in t_utterances]  # TODO: drop .split() after updated
    t2a = target_to_align4d(t_utterances, a_output['reference'][DEFAULT_SPEAKER])
    a2w = align4d_to_whisper(w_tokens, a_output['hypothesis'])
    t2w = target_to_whisper(w_tokens, w_sids, t_speakers, t2a, a2w)
    json.dump(t2w, open(fuse_output, 'w'), indent=2)
    return t2w


def compare(t2w: list[list[str]], t_utterances: list[list[str]]):
    all, idx, empty, nosid = [], 0, 0, 0

    for sid, utterance in t2w:
        if sid:
            all.append('{}: {}'.format(sid, utterance))
            all.append('<- {}'.format(' '.join(t_utterances[idx])))
            if not utterance: empty += 1
            idx += 1
        else:
            all.append('({})'.format(utterance))
            nosid += 1

    fout = open('resources/xprint_5.txt', 'w')
    fout.write('\n'.join(all))
    fout.write('\n\nNo Match: {}, No Speaker: {}\n'.format(empty, nosid))


def fuse_plain(t2w, plain_output: str):
    fout = open(plain_output, 'w')
    for sid, utterance in t2w:
        fout.write('Speaker {}: {}\n'.format(sid, utterance))


if __name__ == '__main__':
    tokenizer = EnglishTokenizer()
    whisper_input = 'resources/whisper.json'
    target_input = 'resources/azure.json'
    fuse_output = 'resources/fuse.json'
    align_output = 'resources/align.json'
    fuse(whisper_input, target_input, fuse_output, tokenizer, align_output)
