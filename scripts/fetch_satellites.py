
import argparse
import http.cookiejar
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode


URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
OMM_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=STATIONS&FORMAT=XML"
OUTPUT_DIR = Path("data/raw")


def fetch_spacetrack():
    """Fetch current GP data from Space-Track and select station-related objects."""
    username = os.getenv("SPACETRACK_USER")
    password = os.getenv("SPACETRACK_PASS")
    if not username or not password:
        raise RuntimeError("Space-Track credentials are not configured.")

    base_url = "https://www.space-track.org"
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )

    login_data = urlencode({
        "identity": username,
        "password": password,
    }).encode("utf-8")
    login_request = urllib.request.Request(
        base_url + "/ajaxauth/login",
        data=login_data,
        headers={
            "User-Agent": "SKYTRACE/1.1",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with opener.open(login_request, timeout=15) as response:
        login_body = response.read().decode("utf-8", errors="replace")
    if "login failed" in login_body.lower():
        raise RuntimeError("Space-Track authentication failed.")

    query_url = (
        base_url
        + "/basicspacedata/query/class/gp/decay_date/null-val/"
        + "epoch/%3Enow-1/format/json"
    )
    query_request = urllib.request.Request(
        query_url,
        headers={"User-Agent": "SKYTRACE/1.1"},
    )
    with opener.open(query_request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        raise RuntimeError("Space-Track returned an unexpected GP response.")

    station_keywords = (
        "ISS", "TIANGONG", "TIANHE", "TIANZHOU",
        "MENGTIAN", "WENTIAN", "CSS",
    )
    lines = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("OBJECT_NAME") or "").strip()
        if not name or not any(
            keyword in name.upper() for keyword in station_keywords
        ):
            continue

        line1 = str(item.get("TLE_LINE1") or "").strip()
        line2 = str(item.get("TLE_LINE2") or "").strip()
        if not line1 or not line2:
            continue

        name_line = str(item.get("TLE_LINE0") or name).strip()
        if name_line.startswith("0 "):
            name_line = name_line[2:]
        lines.extend((name_line, line1, line2))

    if not lines:
        raise RuntimeError(
            "Space-Track returned no usable station-related TLE records."
        )

    provider_records = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("OBJECT_NAME") or "").strip()
        if not name or not any(
            keyword in name.upper() for keyword in station_keywords
        ):
            continue
        provider_records.append({
            "object_name": name,
            "norad_cat_id": str(item.get("NORAD_CAT_ID") or ""),
            "epoch": item.get("EPOCH"),
            "creation_date": item.get("CREATION_DATE"),
            "element_set_no": item.get("ELEMENT_SET_NO"),
        })

    LAST_SPACETRACK_PROVIDER_RECORDS = provider_records
    return "\n".join(lines) + "\n", query_url



def parse_omm_xml(xml_text):
    from io import StringIO
    from sgp4 import omm
    from sgp4.api import Satrec
    if not isinstance(xml_text, str) or not xml_text.strip():
        raise ValueError("OMM XML response is empty.")
    parsed = []
    for fields in omm.parse_xml(StringIO(xml_text)):
        name = str(fields.get("OBJECT_NAME") or fields.get("OBJECT_ID") or "").strip()
        catalog_id = str(fields.get("NORAD_CAT_ID") or "").strip()
        epoch = str(fields.get("EPOCH") or "").strip()
        if not catalog_id.isdigit() or not epoch:
            raise ValueError("OMM record is missing a valid NORAD_CAT_ID or EPOCH.")
        satellite = Satrec()
        omm.initialize(satellite, fields)
        parsed.append({
            "name": name or f"OBJECT {catalog_id}",
            "norad_id": catalog_id,
            "epoch": epoch,
            "fields": dict(fields),
            "satellite": satellite,
        })
    if not parsed:
        raise ValueError("OMM XML contained no usable orbital records.")
    return parsed


def fetch_celestrak_omm():
    request = urllib.request.Request(
        OMM_URL,
        headers={"User-Agent": "SKYTRACE/1.2 OMM data fetcher"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8"), response.geturl()


def tle_checksum(line):
    """Calculate the standard TLE checksum over columns 1-68."""
    if len(line) < 68:
        raise ValueError("TLE line must contain at least 68 characters.")

    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1

    return total % 10


def valid_tle_line(line, line_number):
    """Validate a TLE line's length, line number, and checksum."""
    if len(line) < 69:
        return False

    if line[0] != str(line_number):
        return False

    if not line[68].isdigit():
        return False

    return tle_checksum(line) == int(line[68])


def save_data_pair(
    tle_path: Path,
    metadata_path: Path,
    tle_text: str,
    metadata_text: str,
) -> None:
    """Save both files with backup-based rollback if replacement fails."""
    destinations = (tle_path, metadata_path)
    contents = (tle_text, metadata_text)

    temporary_paths = tuple(
        path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        for path in destinations
    )
    backup_paths = tuple(
        path.with_name(f"{path.name}.{uuid4().hex}.bak")
        for path in destinations
    )

    originals_moved = []
    replacements_installed = []

    try:
        # Stage all new content before touching existing destinations.
        for temp_path, content in zip(temporary_paths, contents):
            temp_path.write_text(content, encoding="utf-8")

        # Preserve any existing destination by moving it to a backup.
        for destination, backup_path in zip(destinations, backup_paths):
            if destination.exists():
                destination.replace(backup_path)
                originals_moved.append((destination, backup_path))

        # Install both staged files.
        for temp_path, destination in zip(temporary_paths, destinations):
            temp_path.replace(destination)
            replacements_installed.append(destination)

    except Exception as save_error:
        rollback_errors = []

        # Remove any new files already installed.
        for destination in reversed(replacements_installed):
            try:
                destination.unlink(missing_ok=True)
            except OSError as error:
                rollback_errors.append(
                    f"Could not remove {destination}: {error}"
                )

        # Restore the original files from their backups.
        for destination, backup_path in reversed(originals_moved):
            try:
                if backup_path.exists():
                    backup_path.replace(destination)
                else:
                    rollback_errors.append(
                        f"Backup missing; cannot restore {destination}"
                    )
            except OSError as error:
                rollback_errors.append(
                    f"Could not restore {destination}: {error}"
                )

        # Remove leftover staging files.
        for temp_path in temporary_paths:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as error:
                rollback_errors.append(
                    f"Could not remove temporary file {temp_path}: {error}"
                )

        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise RuntimeError(
                f"Save failed and rollback was incomplete: {details}"
            ) from save_error

        raise

    # The new pair is installed. Remove backups on a best-effort basis.
    for _, backup_path in originals_moved:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Fetch and validate station orbital data.")
    parser.add_argument("--format", choices=("tle", "omm-xml"), default="tle")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.format == "omm-xml":
        xml_text, source_url = fetch_celestrak_omm()
        records = parse_omm_xml(xml_text)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        data_path = OUTPUT_DIR / f"stations_{stamp}.omm.xml"
        metadata_path = OUTPUT_DIR / f"stations_{stamp}.omm.json"
        metadata = {
            "source": source_url,
            "retrieved_at_utc": retrieved_at,
            "record_count": len(records),
            "format": "OMM-XML",
            "validation": "Parsed and initialized with python-sgp4; not an independent accuracy validation",
        }
        save_data_pair(data_path, metadata_path, xml_text, json.dumps(metadata, indent=2))
        print("\n=== SKYTRACE OMM DATA PIPELINE ===")
        print(f"Records initialized: {len(records)}")
        print(f"Retrieved at UTC:    {retrieved_at}")
        print(f"OMM XML saved:       {data_path}")
        print(f"Metadata saved:      {metadata_path}")
        for record in records[:5]:
            print(f"  {record['norad_id']}  {record['name']}")
        return

    raw_data = None
    source_url = None
    provider_record_timestamps = []

    if os.getenv("SPACETRACK_USER") and os.getenv("SPACETRACK_PASS"):
        try:
            raw_data, source_url = fetch_spacetrack()
            provider_record_timestamps = LAST_SPACETRACK_PROVIDER_RECORDS
            print("Data source: Space-Track")
        except Exception as exc:
            print(
                f"Space-Track fetch failed ({type(exc).__name__}: {exc}); "
                "trying CelesTrak."
            )

    if raw_data is None:
        request = urllib.request.Request(
            URL,
            headers={"User-Agent": "SKYTRACE/1.0 satellite data fetcher"},
        )

        # Retry transient connection failures, but do not hammer the source.
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=8) as response:
                    raw_data = response.read().decode("utf-8")
                    source_url = response.geturl()
                break
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise RuntimeError(
                        f"CelesTrak download failed after 3 attempts: {exc}"
                    ) from exc
                time.sleep(attempt + 1)


    lines = [line.strip() for line in raw_data.splitlines() if line.strip()]

    if len(lines) < 3 or len(lines) % 3 != 0:
        raise ValueError(
            "Unexpected TLE response: expected a name and two TLE lines "
            "for each record."
        )

    records = []

    for index in range(0, len(lines), 3):
        name, line1, line2 = lines[index:index + 3]

        if not line1.startswith("1 ") or not line2.startswith("2 "):
            raise ValueError(f"Malformed TLE lines for record: {name}")

        if not valid_tle_line(line1, 1):
            raise ValueError(f"Invalid line 1 checksum or structure: {name}")

        if not valid_tle_line(line2, 2):
            raise ValueError(f"Invalid line 2 checksum or structure: {name}")

        norad_id_1 = line1[2:7].strip()
        norad_id_2 = line2[2:7].strip()

        if norad_id_1 != norad_id_2:
            raise ValueError(f"Catalog ID mismatch for record: {name}")

        records.append(
            {
                "name": name,
                "norad_id": norad_id_1,
                "line1": line1,
                "line2": line2,
            }
        )

    retrieved_at = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    tle_path = OUTPUT_DIR / f"stations_{stamp}.tle"
    metadata_path = OUTPUT_DIR / f"stations_{stamp}.json"

    metadata_text = json.dumps(
        {
            "source": source_url,
            "retrieved_at_utc": retrieved_at,
            "record_count": len(records),
            "provider_record_timestamps": provider_record_timestamps,
            "format": "TLE",
            "validation": (
                "Structure, catalog IDs, and TLE checksums passed; "
                "not an independent accuracy validation"
            ),
        },
        indent=2,
    )

    save_data_pair(
        tle_path,
        metadata_path,
        "\n".join(lines) + "\n",
        metadata_text,
    )

    print("\n=== SKYTRACE DATA PIPELINE ===")
    print(f"Records validated: {len(records)}")
    print(f"Retrieved at UTC:  {retrieved_at}")
    print(f"TLE data saved:    {tle_path}")
    print(f"Metadata saved:    {metadata_path}")
    print("\nSample objects:")

    for record in records[:5]:
        print(f"  {record['norad_id']}  {record['name']}")


if __name__ == "__main__":
    main()