package com.example.domain;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * 金額。円単位の整数で保持し、マイナスにならない（INV-001, INV-004）。
 * 金額は必ずこの型で受け渡し、double / float は使わない。
 */
public final class Money {

    private final BigDecimal yen;

    private Money(BigDecimal yen) {
        if (yen.signum() < 0) {
            throw new IllegalArgumentException("金額は0円以上で指定してください: " + yen.toPlainString());
        }
        this.yen = yen.setScale(0, RoundingMode.UNNECESSARY);
    }

    public static Money yen(long yen) {
        return new Money(BigDecimal.valueOf(yen));
    }

    public static Money zero() {
        return yen(0);
    }

    public Money plus(Money other) {
        return new Money(this.yen.add(other.yen));
    }

    public Money times(int quantity) {
        if (quantity < 0) {
            throw new IllegalArgumentException("数量は0以上で指定してください: " + quantity);
        }
        return new Money(this.yen.multiply(BigDecimal.valueOf(quantity)));
    }

    /** 率（%）を掛けた金額。1円未満は切り捨てる（REQ-003）。 */
    public Money percent(int rate) {
        if (rate < 0 || rate > 100) {
            throw new IllegalArgumentException("率は0〜100で指定してください: " + rate);
        }
        return new Money(this.yen.multiply(BigDecimal.valueOf(rate)).divide(BigDecimal.valueOf(100), 0, RoundingMode.DOWN));
    }

    /** 差し引いた金額。0円を下回る場合は0円にする（INV-004）。 */
    public Money minusOrZero(Money other) {
        BigDecimal diff = this.yen.subtract(other.yen);
        return new Money(diff.signum() < 0 ? BigDecimal.ZERO : diff);
    }

    public long toLong() {
        return yen.longValueExact();
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof Money other && yen.compareTo(other.yen) == 0;
    }

    @Override
    public int hashCode() {
        return yen.hashCode();
    }

    @Override
    public String toString() {
        return yen.toPlainString() + "円";
    }
}
