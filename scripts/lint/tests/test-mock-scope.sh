#!/usr/bin/env bash
# scripts/lint/common/mock-scope.sh（COMMON-012）の自己テスト。interface のモックは通し、class・record・spy は止める。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; pass=0; fail=0
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
mkdir -p "$w/src/main/java/a" "$w/src/test/java/a"
printf 'package a;\npublic interface ReservationRepository {}\n' > "$w/src/main/java/a/ReservationRepository.java"
printf 'package a;\npublic class CancellationPolicy {}\n' > "$w/src/main/java/a/CancellationPolicy.java"
printf 'package a;\npublic record Money(long v) {}\n' > "$w/src/main/java/a/Money.java"
run() { printf '%s\n' "$1" > "$w/src/test/java/a/XTest.java"; out=$(TAZUNA_ROOT="$w" bash "$ROOT/scripts/lint/common/mock-scope.sh" 2>&1); rc=$?; }
case_() { run "$3"; if { [ "$2" = ok ] && [ $rc -eq 0 ]; } || { [ "$2" = ng ] && [ $rc -ne 0 ]; }; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（rc=$rc）: $out"; fi; }
case_ "interface のモックは通す" ok 'var r = mock(ReservationRepository.class);'
case_ "@Mock の interface は通す" ok '@Mock ReservationRepository repo;'
case_ "外部ライブラリの型は見ない" ok 'var c = mock(java.time.Clock.class); var d = mock(Clock.class);'
case_ "業務ロジックの class は止める" ng 'var p = mock(CancellationPolicy.class);'
case_ "@Mock の class も止める" ng '@Mock private CancellationPolicy policy;'
case_ "record も止める" ng 'Money m = mock(Money.class);'
case_ "spy は止める" ng 'var p = spy(new CancellationPolicy());'
grep -q 'COMMON-012' <<<"$out" && grep -q '修正:' <<<"$out" && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "NG: 理由と直し方を出す"; }
echo "mock-scope: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
