package com.example.domain;

import java.util.Objects;

/**
 * 予約。振込状況は 未振込 → 振込済 → 取消、または 未振込 → 取消 の順にしか進まない。
 * 取消は終端で、他の状態に戻らない（INV-002）。
 */
public final class Reservation {

    public static final int REMARKS_MAX_LENGTH = 80;

    private final String reserveNo;
    private final String tourCode;
    private final int adultCount;
    private final int childCount;
    private final Money sumPrice;
    private final String remarks;
    private TransferStatus status;

    private Reservation(String reserveNo, String tourCode, int adultCount, int childCount, Money sumPrice, String remarks) {
        this.reserveNo = Objects.requireNonNull(reserveNo);
        this.tourCode = Objects.requireNonNull(tourCode);
        this.adultCount = adultCount;
        this.childCount = childCount;
        this.sumPrice = Objects.requireNonNull(sumPrice);
        this.remarks = remarks == null ? "" : remarks;
        this.status = TransferStatus.UNPAID;
    }

    /** 入力条件（REQ-001）を満たす予約だけを作る。 */
    public static Reservation create(String reserveNo, Tour tour, int adultCount, int childCount, String remarks) {
        if (adultCount < 0 || childCount < 0) {
            throw new IllegalArgumentException("人数は0以上で指定してください");
        }
        if (adultCount + childCount == 0) {
            throw new IllegalArgumentException("人数を入力してください");
        }
        if (adultCount == 0) {
            throw new IllegalArgumentException("お子様のみのご予約はお受けできません");
        }
        if (remarks != null && remarks.length() > REMARKS_MAX_LENGTH) {
            throw new IllegalArgumentException("備考は" + REMARKS_MAX_LENGTH + "文字以内で入力してください");
        }
        return new Reservation(reserveNo, tour.code(), adultCount, childCount, tour.priceFor(adultCount, childCount), remarks);
    }

    public void markPaid() {
        if (status != TransferStatus.UNPAID) {
            throw new IllegalStateException("予約 " + reserveNo + " は" + status.label() + "のため振込済にできません");
        }
        status = TransferStatus.PAID;
    }

    public void cancel() {
        if (status == TransferStatus.CANCELLED) {
            throw new IllegalStateException("予約 " + reserveNo + " は取り消し済みです");
        }
        status = TransferStatus.CANCELLED;
    }

    public int headcount() {
        return adultCount + childCount;
    }

    public String reserveNo() {
        return reserveNo;
    }

    public String tourCode() {
        return tourCode;
    }

    public Money sumPrice() {
        return sumPrice;
    }

    public String remarks() {
        return remarks;
    }

    public TransferStatus status() {
        return status;
    }
}
