
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
OUTPUT_DIR = Path("data/raw")


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
    parser = argparse.ArgumentParser(
        description="Fetch, validate, and save station TLE data."
    )
    parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "SKYTRACE/1.0 satellite data fetcher"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw_data = response.read().decode("utf-8")
        source_url = response.geturl()

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