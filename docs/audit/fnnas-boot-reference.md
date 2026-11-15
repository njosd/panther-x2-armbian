# FNNAS Panther X2 boot reference archive

## Source and handling

- Source archive: `fnnas-boot-reference-20261115-200307.tar.gz`
- Original repository location: repository root on `workflow/fnnas-reference-audit`
- Canonical location: `audit/reference-boot/fnnas/fnnas-boot-reference-20261115-200307.tar.gz`
- Archive Git blob SHA-1: `57fdd693703f8e3a9ff317f3e70293a0b3ac31b3`
- The archive is preserved byte-for-byte during the repository move.

The source TF boot partition was automatically mounted read-write after insertion and EXT4 journal recovery completed. It was subsequently remounted read-only before the boot files were collected. Therefore, collection was not read-only from the instant of insertion; the later inspection/copy was performed after the read-only remount.

## Audit boundary

The GitHub Actions workflow validates the gzip stream, lists and extracts archive members into a disposable runner directory, computes SHA256 hashes, verifies a supplied checksum manifest if present, and conditionally inspects boot configuration and the Panther X2 DTB.

It does not execute scripts from the archive, access a physical TF card, connect to Panther X2, or modify any device. CI results are evidence about the uploaded archive only; they do not establish that the original TF card remained untouched before the read-only remount.
