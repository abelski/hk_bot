# thesurfr.app API Reference

Reverse-engineered from `spot.thesurfr.app` (Next.js SPA).

Real backend: `https://devapi.thesurfr.app`  
All calls go through Next.js proxy routes at `https://spot.thesurfr.app/api/proxy/*`.

---

## Key Parameters

| Param | Meaning |
|---|---|
| `spotid` / `spotId` | Internal Surfr spot ID (e.g. `12930`) |
| `wgspotid` | Windguru spot ID (e.g. `558162`) |
| `leaderboardSpotsId` | Additional spot IDs merged into leaderboard |
| `liveSpotsId` | Additional spot IDs merged into live view |
| `period` | `daily` / `monthly` / `alltime` |
| `gender` | `female` (omit for all genders) |

---

## Leaderboard

### `GET /api/proxy/leaderboard/height`

Ranked list of riders by jump height.

```
?period=daily|monthly|alltime
&offset=0
&spotid=12930
&additionalSpotsId=12930    (optional, merge extra spots)
&gender=female              (optional)
```

Response: array of rider objects with jump height, user profile, kite/board gear info.

---

### `GET /api/proxy/leaderboard/stats`

Aggregate session stats for a spot.

```
?spotid=12930
&period=daily|monthly|alltime
&date=2026-04-21
&gender=female              (optional)
```

Response:
```json
[{ "numsession": 3, "totaltimeonwater": 7865, "uniqueusers": 3 }]
```

---

### `GET /api/proxy/leaderboard/hero`

Top rider (most sessions) at a spot.

```
?spotid=12930
&additionalSpotsId=12930    (optional)
&gender=female              (optional)
```

Response:
```json
[{
  "numsessions": 97,
  "userid": 55447,
  "name": "Denis",
  "alpha2": "RU",
  "profilepicid": "913c9083-...",
  "ispro": false,
  "spotId": 12930,
  "spotName": "Viz-ekb"
}]
```

---

## Live Data

### `GET /api/proxy/live`

Currently active riders on the water. Polled every 30s when active.

```
?spotId=12930
&sort=live.lastjumpupdate   (default sort key)
&additionalSpotsId=12930    (optional)

# Alternative: bounding box instead of spotId
?useArea=true
&neLat=&neLng=&swLat=&swLng=
```

Response:
```json
{ "success": true, "riders": [], "spotName": "Viz-ekb" }
```

---

### `GET /api/proxy/statistics`

Spot-level statistics — total riders and kite brand distribution.

```
?spotid=12930
&additionalSpotsId=12930    (optional)
```

Response:
```json
{ "totalRiders": 0, "kiteStats": [{ "brand": "Cabrinha", "count": 5, "percentage": 42 }] }
```

---

## Spot Discovery

### `GET /api/proxy/spots/filtered`

Find spots near a GPS coordinate.

```
?lat=56.71&lon=60.63&distance=20
```

Response: array of spot objects with full stats:

```json
{
  "id": 898,
  "name": "Виз (пси)",
  "latitude": 56.7136935877801,
  "longitude": 60.63686454664836,
  "distance": 588.13,
  "countryName": "Russian Federation",
  "alpha2": "RU",
  "riderslive": 0,
  "totalsessions": 0,
  "monthsessions": 0,
  "maxheight": 0,
  "maxairtime": 0,
  "maxdistance": 0,
  "maxspeed": 0,
  "maxleaderboard": 0,
  "wgspotid": 0,
  "wgLiveId": 0,
  "hasWindAlert": false
}
```

---

## Wind Forecast (Windguru proxies)

### `GET /api/windguru-html-axios`

Hourly forecast data (~179 points, ~7 days ahead).

```
?wgspotid=558162
```

Response:
```json
{
  "success": true,
  "initstamp": 1776751200,
  "stepSeconds": 3600,
  "sunriseSunset": { "sunrise": "05:38", "sunset": "20:13" },
  "windSpeedSeries":    [{ "ts": 1776751200, "value": 8.2 }, ...],
  "windGustSeries":     [{ "ts": 1776751200, "value": 16.7 }, ...],
  "windDirSeries":      [{ "ts": 1776751200, "value": 98 }, ...],
  "temperatureSeries":  [{ "ts": 1776751200, "value": 1.3 }, ...],
  "humiditySeries":     [{ "ts": 1776751200, "value": 84 }, ...],
  "cloudCoverSeries":   [{ "ts": 1776751200, "value": null }, ...],
  "precipitationSeries": null
}
```

`ts` is a Unix timestamp. `windDirSeries` values are degrees (0–360).

---

### `GET /api/windguru-spot`

Spot metadata.

```
?id_spot=558162
```

Response:
```json
{
  "success": true,
  "message": "Successfully fetched spot details",
  "tideData": [],
  "gmtHourOffset": 5,
  "dataSource": "windguru-spot"
}
```

---

## Assets

| Resource | URL |
|---|---|
| Profile picture | `https://devapi.thesurfr.app/image/profile/{profilepicid}` |
| Country flag | `https://flagcdn.com/w320/{alpha2}.png` |
| QR code | `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url}` |
| App version | `https://spot.thesurfr.app/version.json?_t={timestamp}` |

---

## Example: Spot Used for Reverse Engineering

| Field | Value |
|---|---|
| Spot name | КитеТим — Территория Ветра |
| `spotid` | `898` |
| `wgspotid` | `558162` |
| `leaderboardSpotsId` | `12930` |
| `liveSpotsId` | `12930` |
| Lat/Lon | `56.7136935877801`, `60.63686454664836` |
