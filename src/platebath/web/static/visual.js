function renderVisual(target, data) {
    const boundaries = [1,2,2.3,3.5];
    const bins = ['＜1','1–2','2–2.3','2.3–3.5','≥3.5'];
    const counts = bins.map(() => 0);
    for (const row of data.rows) {
        const slot = boundaries.findIndex(edge => row.estimate < edge);
        counts[slot < 0 ? bins.length - 1 : slot]++;
    }
    const peak = Math.max(...counts,1);
    const chart = node('div',undefined,'histogram');
    bins.forEach((label,index) => {
        const cell = node('figure');
        const guide = node('div',undefined,'bucket-column');
        const value = node('b',counts[index],index >= 3 ? 'at-threshold' : '');
        value.style.height = `${Math.max(23,Math.round(115 * counts[index] / peak))}px`;
        value.title = `${label} μm · ${counts[index]} 批`;
        guide.append(value);
        cell.append(guide,node('figcaption',label));
        chart.append(cell);
    });
    target.append(chart);
}
