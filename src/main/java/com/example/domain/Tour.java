package com.example.domain;

import java.time.LocalDate;
import java.util.Objects;

/**
 * ツアー。残席数はマイナスにならない（INV-003）。
 * 残席数は予約で減り、取消で戻る。直接書き換えるセッターは用意しない。
 */
public final class Tour {

    private final String code;
    private final String name;
    private final LocalDate departureDate;
    private final Money adultPrice;
    private final Money childPrice;
    private int remainingSeats;

    public Tour(String code, String name, LocalDate departureDate, Money adultPrice, Money childPrice, int remainingSeats) {
        if (remainingSeats < 0) {
            throw new IllegalArgumentException("残席数は0以上で指定してください: " + remainingSeats);
        }
        this.code = Objects.requireNonNull(code);
        this.name = Objects.requireNonNull(name);
        this.departureDate = Objects.requireNonNull(departureDate);
        this.adultPrice = Objects.requireNonNull(adultPrice);
        this.childPrice = Objects.requireNonNull(childPrice);
        this.remainingSeats = remainingSeats;
    }

    /** 席を確保する。残席を超える場合は確保しない（INV-003）。 */
    public void reserveSeats(int count) {
        if (count > remainingSeats) {
            throw new IllegalStateException("残席が不足しています（残席 " + remainingSeats + "、予約 " + count + "）");
        }
        remainingSeats -= count;
    }

    /** 取消された予約の席を戻す。 */
    public void releaseSeats(int count) {
        remainingSeats += count;
    }

    /** 合計金額 = 大人料金 × 大人人数 + 子供料金 × 子供人数。 */
    public Money priceFor(int adultCount, int childCount) {
        return adultPrice.times(adultCount).plus(childPrice.times(childCount));
    }

    public String code() {
        return code;
    }

    public String name() {
        return name;
    }

    public LocalDate departureDate() {
        return departureDate;
    }

    public int remainingSeats() {
        return remainingSeats;
    }
}
