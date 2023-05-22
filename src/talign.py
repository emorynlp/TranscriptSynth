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
from typing import Optional, List, Dict

from align4d import align


def alignt():
    hypothesis = "ok I am a fish. Are you? Hello there. How are you? ok"
    reference = [
        ["A", "I am a fish. "],
        ["B", "okay. "],
        ["C", "Are you? "],
        ["D", "Hello there. "],
        ["E", "How are you? "]
    ]
    align_result = align.align(hypothesis, reference)
    print(align_result)


def fuse(source: List[Dict], target: List[Dict]):
    """
    :param source: the list of utterances without speaker information.
    :param target: the list of utterances with speaker information.
    :return:
    """
    s_tokens = [token for line in source for token in line.split()]



if __name__ == '__main__':
    fuse()
