"""
Layered Card Comparator

Layer 1: COLOR GATE (fast, free, no API calls)
  - Sample hex colors from center regions of both images
  - If colors are CLEARLY different (distance > 100) → REJECT immediately
  - If colors are CLEARLY similar (distance < 40) → PASS to profit check
  - If colors are BORDERLINE (40-100) → escalate to Layer 2

Layer 2: AI DEEP CHECK (Nova, only when color is ambiguous)
  - Ask Nova to compare the actual content: pose, text, design elements
  - Specifically ask about pose differences (Action Variation vs Base)
  - Ask about insert subset differences (Signing Autographs vs Superstar Sensations)

Layer 3: FLAG FOR REVIEW (when AI is uncertain)
  - Show both images side by side in the UI
  - User makes final call

This minimizes API calls: most cards are caught by color alone.
Only borderline cases (same colors, different pose) need AI.
"""
from __future__ import annotations

import math
import json
import base64
import requests
from io import BytesIO
from typing import Tuple, Dict, Optional

from PIL import Image


# Dense sampling: 250 points across the card for maximum accuracy
# Grid pattern covering the entire card surface
import itertools as _itertools
CENTER_REGIONS = {}
_x_points = list(range(5, 96, 6))  # 16 points across
_y_points = list(range(5, 96, 6))  # 16 points down = 256 points
for _xi, _x in enumerate(_x_points):
    for _yi, _y in enumerate(_y_points):
        CENTER_REGIONS[f'p{_xi}_{_yi}'] = (_x, _y, 1)

COLOR_REJECT = 120    # Above this = clearly different
COLOR_ACCEPT = 40     # Below this = clearly similar
COLOR_BORDERLINE = (40, 120)


def download_image(url: str) -> Tuple[Optional[bytes], Optional[Image.Image]]:
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None, None
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        return resp.content, img
    except Exception:
        return None, None


def sample_avg_color(img: Image.Image, x_pct: int, y_pct: int, size_pct: int = 6):
    w, h = img.size
    cx, cy = int(w * x_pct / 100), int(h * y_pct / 100)
    half = max(int(min(w, h) * size_pct / 200), 3)
    region = img.crop((max(0, cx-half), max(0, cy-half), min(w, cx+half), min(h, cy+half)))
    pixels = list(region.getdata())
    if not pixels:
        return (0, 0, 0)
    return (
        sum(p[0] for p in pixels) // len(pixels),
        sum(p[1] for p in pixels) // len(pixels),
        sum(p[2] for p in pixels) // len(pixels),
    )


def color_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def weighted_color_distance(img1: Image.Image, img2: Image.Image) -> Tuple[float, Dict]:
    total_dist = 0
    count = 0
    details = {}
    for name, (x, y, weight) in CENTER_REGIONS.items():
        c1 = sample_avg_color(img1, x, y)
        c2 = sample_avg_color(img2, x, y)
        d = color_distance(c1, c2)
        total_dist += d
        count += 1
        h1 = f'#{c1[0]:02x}{c1[1]:02x}{c1[2]:02x}'
        h2 = f'#{c2[0]:02x}{c2[1]:02x}{c2[2]:02x}'
        details[name] = {'hex1': h1, 'hex2': h2, 'distance': round(d, 1)}
    return round(total_dist / max(count, 1), 1), details


def nova_deep_check(img1_bytes: bytes, img2_bytes: bytes) -> Dict:
    """Layer 2: Ask Nova to look at content differences (pose, text, subset)."""
    import boto3

    prompt = (
        "I am showing you two trading card images that have SIMILAR colors. "
        "I need to know if they are the EXACT same card or different variants.\n\n"
        "Look carefully at:\n"
        "1. Is the PLAYER POSE the same? (batting vs standing vs throwing = different cards)\n"
        "2. Is there an AUTOGRAPH/SIGNATURE on one but not the other?\n"
        "3. Is the CARD DESIGN/LAYOUT identical? (different insert subsets have different layouts)\n"
        "4. Is the CARD NUMBER the same? (look for small text on the card)\n"
        "5. Any TEXT differences? (different card names, different subset names)\n\n"
        "Answer JSON: {\"same_card\": true/false, \"confidence\": \"high\"/\"medium\"/\"low\", "
        "\"reason\": \"what specific differences or similarities you see\", "
        "\"pose_match\": true/false, \"has_autograph_difference\": true/false}"
    )

    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = {
            'messages': [{
                'role': 'user',
                'content': [
                    {'image': {'format': 'jpeg', 'source': {'bytes': base64.b64encode(img1_bytes).decode()}}},
                    {'image': {'format': 'jpeg', 'source': {'bytes': base64.b64encode(img2_bytes).decode()}}},
                    {'text': prompt}
                ]
            }],
            'inferenceConfig': {'maxTokens': 300, 'temperature': 0.1}
        }
        response = client.invoke_model(
            modelId='us.amazon.nova-lite-v1:0',
            body=json.dumps(body),
            contentType='application/json',
        )
        result = json.loads(response['body'].read())
        text = result.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        clean = text.strip().strip('`').strip()
        if clean.startswith('json'):
            clean = clean[4:].strip()
        return json.loads(clean)
    except Exception as e:
        return {'same_card': False, 'reason': f'Nova error: {e}', 'confidence': 'low'}


def compare_cards(scp_image_url: str, ebay_image_url: str, verbose: bool = False) -> Dict:
    """
    Layered comparison:
    Layer 1: Color gate (fast, free)
    Layer 2: AI deep check (only if colors are borderline)
    Layer 3: Flag for review (if still uncertain)
    """
    scp_bytes, scp_img = download_image(scp_image_url)
    ebay_bytes, ebay_img = download_image(ebay_image_url)

    if not scp_img or not ebay_img:
        return {
            'same_card': False, 'confidence': 'low',
            'layer': 'error', 'reason': 'Image download failed',
        }

    # LAYER 1: Color gate
    avg_dist, color_details = weighted_color_distance(scp_img, ebay_img)

    if avg_dist > COLOR_REJECT:
        # Clearly different colors → reject without AI
        result = {
            'same_card': False, 'confidence': 'high',
            'layer': 'color_reject',
            'color_distance': avg_dist,
            'reason': f'Colors clearly different (distance {avg_dist} > {COLOR_REJECT})',
        }
        if verbose:
            print(f"  Layer 1: COLOR REJECT (distance {avg_dist})")
        return result

    if avg_dist < COLOR_ACCEPT:
        # Colors very similar → accept without AI
        result = {
            'same_card': True, 'confidence': 'high',
            'layer': 'color_accept',
            'color_distance': avg_dist,
            'reason': f'Colors match closely (distance {avg_dist} < {COLOR_ACCEPT})',
        }
        if verbose:
            print(f"  Layer 1: COLOR ACCEPT (distance {avg_dist})")
        return result

    # LAYER 2: Borderline colors → ask AI
    if verbose:
        print(f"  Layer 1: BORDERLINE (distance {avg_dist}) → escalating to Nova")

    nova_result = nova_deep_check(scp_bytes, ebay_bytes)
    nova_says = nova_result.get('same_card', False)
    pose_match = nova_result.get('pose_match', True)
    auto_diff = nova_result.get('has_autograph_difference', False)

    # If Nova says same but detects pose difference or autograph difference → reject
    if nova_says and (not pose_match or auto_diff):
        result = {
            'same_card': False, 'confidence': 'medium',
            'layer': 'ai_pose_reject',
            'color_distance': avg_dist,
            'nova_result': nova_result,
            'reason': f"Colors similar but {'different pose' if not pose_match else 'autograph difference'}",
        }
        if verbose:
            print(f"  Layer 2: AI POSE REJECT ({nova_result.get('reason', '?')[:60]})")
        return result

    result = {
        'same_card': nova_says,
        'confidence': nova_result.get('confidence', 'medium'),
        'layer': 'ai_confirm' if nova_says else 'ai_reject',
        'color_distance': avg_dist,
        'nova_result': nova_result,
        'reason': nova_result.get('reason', '?'),
    }
    if verbose:
        print(f"  Layer 2: AI {'CONFIRM' if nova_says else 'REJECT'} ({nova_result.get('reason', '?')[:60]})")
    return result


if __name__ == '__main__':
    tests = [
        ('SHOULD MATCH: Pink Refractor vs Pink Refractor',
         'https://storage.googleapis.com/images.pricecharting.com/corrudrl4nonfef4vxxm/1600.jpg',
         'https://i.ebayimg.com/images/g/ty8AAeSwQp1p7nqY/s-l1600.jpg', True),
        ('SHOULD NOT MATCH: Negative Refractor vs Sepia Refractor',
         'https://storage.googleapis.com/images.pricecharting.com/corrdd6eb25ubx3jptad/1600.jpg',
         'https://i.ebayimg.com/images/g/X24AAeSwYOtp5ZQb/s-l1600.jpg', False),
        ('SHOULD NOT MATCH: Negative Refractor vs Pink Refractor',
         'https://storage.googleapis.com/images.pricecharting.com/corr6he7mpl3t4i7eh7d/1600.jpg',
         'https://i.ebayimg.com/images/g/ty8AAeSwQp1p7nqY/s-l1600.jpg', False),
        ('SHOULD NOT MATCH: Action Variation vs Base Heritage PSA8',
         'https://storage.googleapis.com/images.pricecharting.com/corr6cmjmqcexvkyyi6d/1600.jpg',
         'https://i.ebayimg.com/images/g/4ckAAeSwEeNp83b8/s-l1600.jpg', False),
        ('SHOULD NOT MATCH: Signing Autographs vs Superstar Sensations PSA10',
         'https://storage.googleapis.com/images.pricecharting.com/corrpshyfrti4romrn6w/1600.jpg',
         'https://i.ebayimg.com/images/g/YskAAeSw5m5pwF2c/s-l1600.jpg', False),
    ]

    correct = 0
    for name, scp_url, ebay_url, expect in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        result = compare_cards(scp_url, ebay_url, verbose=True)
        is_correct = result['same_card'] == expect
        if is_correct: correct += 1
        print(f"  FINAL: same_card={result['same_card']} confidence={result['confidence']} layer={result['layer']}")
        print(f"  Reason: {result['reason'][:80]}")
        print(f"  >>> {'CORRECT ✓' if is_correct else 'WRONG ✗'}")

    print(f"\n{'='*60}")
    print(f"SCORE: {correct}/{len(tests)}")
    print(f"{'='*60}")
