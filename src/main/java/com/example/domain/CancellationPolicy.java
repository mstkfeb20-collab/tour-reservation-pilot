package com.example.domain;

/**
 * 取消料率表（REQ-003）。
 *
 * <pre>
 * 出発日の 21日前まで    0%
 *          20日前〜8日前 20%
 *          7日前〜2日前  30%
 *          前日          40%
 *          当日以降      取消不可（REQ-002）
 * </pre>
 */
public final class CancellationPolicy {

    private CancellationPolicy() {
    }

    /** 取消できるのは出発日の前日まで（REQ-002）。 */
    public static boolean canCancel(long daysBeforeDeparture) {
        return daysBeforeDeparture >= 1;
    }

    /** 取消料率（%）。 */
    public static int rate(long daysBeforeDeparture) {
        if (!canCancel(daysBeforeDeparture)) {
            throw new IllegalArgumentException("出発日の当日以降は取り消せません");
        }
        if (daysBeforeDeparture >= 21) {
            return 0;
        }
        if (daysBeforeDeparture >= 8) {
            return 20;
        }
        if (daysBeforeDeparture >= 2) {
            return 30;
        }
        return 40;
    }

    /** 取消料。 */
    public static Money fee(Reservation reservation, long daysBeforeDeparture) {
        return reservation.sumPrice().percent(rate(daysBeforeDeparture));
    }

    public static Money refund(Money paid, Money fee) {
        return paid.minusOrZero(fee);
    }

    public static Money claim(Money paid, Money fee) {
        return fee.minusOrZero(paid);
    }
}
