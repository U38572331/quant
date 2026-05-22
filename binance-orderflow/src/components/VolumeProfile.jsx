import React from 'react';

const VolumeProfile = ({ data }) => {
    if (!data) return null;

    // Convert map to sorted array of [price, volume]
    const profile = Object.entries(data)
        .sort((a, b) => parseFloat(b[0]) - parseFloat(a[0]));

    const maxVol = Math.max(...Object.values(data), 1);

    return (
        <div className="flex flex-col h-full bg-dark-bg text-[10px] font-mono overflow-y-auto">
            {profile.map(([price, vol]) => (
                <div key={price} className="h-5 flex items-center relative border-b border-grid-line/10 hover:bg-white/5 pr-2">
                    {/* Background Bar */}
                    <div
                        className="absolute right-0 top-0 bottom-0 bg-accent-blue/20 border-l border-accent-blue/40"
                        style={{ width: `${(vol / maxVol) * 100}%` }}
                    ></div>

                    <div className="z-10 w-16 text-right px-2 text-text-secondary border-r border-grid-line/30">
                        {parseFloat(price).toFixed(1)}
                    </div>
                    <div className="z-10 flex-1 text-right px-2 text-text-primary">
                        {vol.toFixed(2)}
                    </div>
                </div>
            ))}

            {profile.length === 0 && (
                <div className="p-4 text-center text-text-secondary italic">
                    Collecting session data...
                </div>
            )}
        </div>
    );
};

export default VolumeProfile;
