# Landmark API

Landmark 모듈은 메시 엣지 기반의 랜드마크 데이터를 제공한다.
다른 모듈(wrapping, rigging 등)은 이 API를 통해 랜드마크 데이터를 가져간다.

---

## 데이터 구조

### 메시 속성

랜드마크는 Blender 메시의 **INT 엣지 속성**으로 저장된다.

- 속성 이름: `lm__{그룹이름}` (공백/점은 `_`로 치환)
- 값: `1` = 마킹됨, `0` = 마킹 안 됨
- 예: `"Elbow Line.L"` → 속성 이름 `lm__Elbow_Line_L`

### Scene 프로퍼티

```python
scene.intra10_landmark_groups   # CollectionProperty — 그룹 목록
scene.intra10_landmark_groups[i].name      # str  — 그룹 이름
scene.intra10_landmark_groups[i].color     # float[4] — RGBA 색상
scene.intra10_landmark_groups[i].obj_name  # str  — 소속 오브젝트 이름
scene.intra10_landmark_groups[i].visible   # bool — 뷰포트 표시 여부
```

---

## Python API

### 1. 그룹 centroid 가져오기

```python
from landmark import landmark_core

obj = bpy.context.active_object
centroid = landmark_core.get_group_centroid(obj, "Elbow Line.L")
# → mathutils.Vector (월드 좌표) 또는 None
```

- 마킹된 모든 엣지의 중점(midpoint)을 평균한 좌표
- 오브젝트 모드 / 편집 모드 모두 동작
- `obj.matrix_world`가 적용된 **월드 좌표**를 반환

### 2. 마킹된 엣지 인덱스 가져오기

```python
indices = landmark_core.get_marked_edge_indices(obj, "Elbow Line.L")
# → [1523, 1524, 1530, ...] 또는 []
```

- 해당 그룹에 마킹된 엣지 인덱스 목록 반환

### 3. 전체 오브젝트의 랜드마크 포인트 순회

```python
scene = bpy.context.scene
obj = bpy.context.active_object

for group in scene.intra10_landmark_groups:
    if group.obj_name != obj.name:
        continue
    centroid = landmark_core.get_group_centroid(obj, group.name)
    if centroid:
        print(f"{group.name}: {centroid}")
```

### 4. 속성 이름 변환

```python
from landmark.landmark_defs import attr_name

attr_name("Elbow Line.L")  # → "lm__Elbow_Line_L"
```

---

## JSON Export

UI의 **Export Points** 버튼 또는 코드에서 직접 호출:

```python
from landmark import landmark_presets

# 오브젝트 모드에서 실행
success, msg = landmark_presets.export_landmark_points(
    "C:/path/to/output.json", obj, scene
)
```

### JSON 포맷

```json
{
  "version": 1,
  "object": "BodyMesh",
  "vertex_count": 12345,
  "landmark_points": [
    {
      "name": "Elbow Line.L",
      "position": [0.45, 0.92, -0.12],
      "color": [0.95, 0.85, 0.1, 1.0],
      "edge_count": 14
    }
  ]
}
```

| 필드 | 설명 |
|------|------|
| `version` | 포맷 버전 (현재 `1`) |
| `object` | 소스 오브젝트 이름 |
| `vertex_count` | 메시 버텍스 수 — 동일 메시 확인용 |
| `name` | 랜드마크 그룹 이름 |
| `position` | `[x, y, z]` 월드 좌표 centroid |
| `color` | `[r, g, b, a]` 0~1 범위 |
| `edge_count` | 마킹된 엣지 수 — centroid 신뢰도 참고 |

---

## 외부 모듈에서 활용 예시

### 조인트 위치 매핑

```python
import json

with open("body_landmark_points.json", "r") as f:
    data = json.load(f)

joint_map = {}
for pt in data["landmark_points"]:
    joint_map[pt["name"]] = pt["position"]

# "Elbow Line.L" → elbow joint 위치로 사용
# "Knee Line.R"  → knee joint 위치로 사용
```

### 소스↔타겟 매칭 (향후 wrapping/transfer 용)

```python
import json

with open("source_landmark_points.json", "r") as f:
    source = json.load(f)
with open("target_landmark_points.json", "r") as f:
    target = json.load(f)

# 같은 이름의 랜드마크끼리 매칭
src_map = {pt["name"]: pt["position"] for pt in source["landmark_points"]}
tgt_map = {pt["name"]: pt["position"] for pt in target["landmark_points"]}

pairs = []
for name in src_map:
    if name in tgt_map:
        pairs.append((name, src_map[name], tgt_map[name]))
```
