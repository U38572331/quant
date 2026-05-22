import React from 'react';

const DOMLadder = ({ orderBook }) => {
    if (!orderBook) return null;

    const { bids, asks } = orderBook;

    // Sort asks descending (highest on top) and bids descending
    const sortedAsks = [...asks].sort((a, b) => b.price - a.price);
    const sortedBids = [...bids].sort((a, b) => b.price - a.price);

    const maxQty = Math.max(
        ...asks.map(a => a.quantity),
        ...bids.map(b => b.quantity),
        1
    );

    const Row = ({ item, type }) => {
        const percent = (item.quantity / maxQty) * 100;
        const color = type === 'ask' ? 'rgba(246, 70, 93, 0.4)' : 'rgba(29, 191, 115, 0.4)';
        const textColor = type === 'ask' ? 'text-sell-red' : 'text-buy-green';

        return (
            <div className="flex h-6 items-center border-b border-grid-line/10 hover:bg-white/5 relative group cursor-default">
                {/* Liquidity Bar */}
                <div
                    className="absolute right-0 top-0 bottom-0 transition-all duration-300"
                    style={{
                        width: `${percent}%`,
                        backgroundColor: color,
                        borderLeft: `1px solid ${type === 'ask' ? 'rgba(246, 70, 93, 0.6)' : 'rgba(29, 191, 115, 0.6)'}`
                    }}
                />

                {/* Price Label */}
                <div className={`z-10 w-24 px-2 font-bold ${textColor}`}>
                    {item.price.toFixed(2)}
                </div>

                {/* Quantity Label */}
                <div className="z-10 flex-1 text-right px-2 font-mono text-[10px] text-text-primary">
                    {item.quantity.toFixed(4)}
                </div>

                {/* Hover Indicator */}
                <div className="absolute inset-0 border border-transparent group-hover:border-white/20 pointer-events-none" />
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-dark-bg font-mono text-[11px] overflow-hidden select-none">
            {/* Asks Section */}
            <div className="flex-1 overflow-y-auto flex flex-col-reverse border-b border-grid-line/30">
                {sortedAsks.map((ask, i) => (
                    <Row key={`ask-${i}`} item={ask} type="ask" />
                ))}
            </div>

            {/* Spread Indicator */}
            <div className="h-8 bg-grid-line/10 flex items-center justify-center text-[10px] text-text-secondary uppercase tracking-widest border-y border-grid-line/20">
                Spread: {(asks[0]?.price - bids[0]?.price || 0).toFixed(1)}
            </div>

            {/* Bids Section */}
            <div className="flex-1 overflow-y-auto">
                {sortedBids.map((bid, i) => (
                    <Row key={`bid-${i}`} item={bid} type="bid" />
                ))}
            </div>
        </div>
    );
};

export default DOMLadder;
