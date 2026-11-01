# Demo 2 stress test

Compared the sample bank with two larger programs from [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo) (Apache-2.0). CardDemo is a mainframe card-management application, bigger than the bank in `backend/src/legacylift/data/`.

Times are from one local run of the API with `DATABASE_URL` unset and the runner off. Verify therefore returns `not_verified` immediately. It does not compile COBOL. Upload, analyze, and convert are the in-process API.

The sample bank is 10 files and 367 lines (15,226 bytes): five programs, three copybooks, and two data files.

| Case | Files | Lines | Bytes | Upload | Analyze | Convert | Verify |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sample bank | 10 | 367 | 15,226 | 0.026s | 0.005s | 0.006s | 0.004s |
| CardDemo `CBTRN02C` plus `CVACT01Y`, `CVACT03Y`, `CVTRA01Y`, `CVTRA05Y`, `CVTRA06Y` | 6 | 817 | 65,550 | 0.026s | 0.006s | 0.008s | 0.006s |
| CardDemo `CBTRN03C` plus `CVACT03Y`, `CVTRA03Y`, `CVTRA04Y`, `CVTRA05Y`, `CVTRA07Y` | 6 | 776 | 62,527 | 0.003s | 0.005s | 0.007s | 0.005s |

Both CardDemo programs finished the flow. Analyze left 60 unresolved names on `CBTRN02C` and 72 on `CBTRN03C` (paragraph `PERFORM`s, `CALL`s such as `CEE3ABD`, and copybooks that were not in the upload). Convert returned `review_required`: 242 notes for `CBTRN02C` and 260 for `CBTRN03C`. The sample bank convert also returned `review_required`, with 29 notes. Verify was `not_verified` with `passed: null` in every case because the runner was off.

## Problems

- Programs over 100 KB never get past upload. `COACTUPC.cbl` (4,236 lines, 186,699 bytes), `COCRDUPC.cbl` (1,560 lines, 127,521 bytes), and `COCRDLIC.cbl` (1,459 lines, 118,835 bytes) each came back in about 0.003s with `400` and `is larger than 100 KB`. Analyze, convert, and verify did not run.
- `COACTVWC.cbl` (941 lines) and `COCRDSLC.cbl` (887 lines) upload and analyze, then convert returns `400`: `File needs PROGRAM-ID and PROCEDURE DIVISION.` In those files the name sits on the line after `PROGRAM-ID.` That is already [issue #97](https://github.com/aadituh/LegacyLift/issues/97).
