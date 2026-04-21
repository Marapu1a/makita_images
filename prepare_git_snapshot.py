from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def walk_image_roots() -> list[Path]:
    roots: list[Path] = []

    roots.extend(
        path for path in ROOT.rglob("import_images") if path.is_dir()
    )

    for relative in ("upload/vvm_images/accessories", "upload/vvm_images/instruments"):
        path = ROOT / relative
        if path.is_dir():
            roots.append(path)

    # Keep a stable order and avoid duplicates when nested scans overlap.
    unique: dict[Path, None] = {}
    for path in sorted(roots):
        unique[path] = None
    return list(unique.keys())


def ensure_gitkeep_files(root: Path) -> tuple[int, int]:
    directory_count = 0
    created_count = 0

    if root.is_dir():
        keep = root / ".gitkeep"
        if not keep.exists():
            keep.touch()
            created_count += 1
        directory_count += 1

    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        directory_count += 1
        keep = path / ".gitkeep"
        if keep.exists():
            continue
        keep.touch()
        created_count += 1

    return directory_count, created_count


def main() -> None:
    roots = walk_image_roots()
    if not roots:
        print("No image roots found.")
        return

    total_directories = 0
    total_created = 0

    print("Preparing git snapshot for image directory topology:")
    for root in roots:
        directories, created = ensure_gitkeep_files(root)
        total_directories += directories
        total_created += created
        print(f"- {root.relative_to(ROOT)}: directories={directories}, created={created}")

    print(
        f"Done. roots={len(roots)} directories={total_directories} gitkeeps_created={total_created}"
    )


if __name__ == "__main__":
    main()
