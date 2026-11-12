(() => {
    // PSA PSGC municipality 0500513000, accessed 2026-11-08.
    // https://psa.gov.ph/classification/psgc/barangays/0500513000
    // No purok names are inferred from this barangay-level dataset.
    const barangays = [
        'Agol', 'Alabangpuro', 'Basicao Coastal', 'Basicao Interior',
        'Banawan', 'Binodegahan', 'Buenavista', 'Buyo', 'Caratagan',
        'Cuyaoyao', 'Flores', 'Lawinon', 'Macasitas', 'Malapay',
        'Malidong', 'Mamlad', 'Marigondon', 'Matanglad', 'Nablangbulod',
        'Oringon', 'Palapas', 'Panganiran', 'Barangay I', 'Barangay II',
        'Barangay III', 'Barangay IV', 'Barangay V', 'Rawis', 'Salvacion',
        'Santo Cristo', 'Sukip', 'Tibabo', 'La Medalla'
    ].sort((a, b) => a.localeCompare(b));
    const input = document.getElementById('location');
    const list = document.getElementById('pio-duran-locations');
    if (!input || !list) return;
    function update() {
        const value = input.value;
        if (!value.trim()) { list.replaceChildren(); return; }
        const parts = value.split(',');
        // Preserve manually entered purok/street instead of replacing it.
        const typingPurok = parts.length === 1 && /^purok\b/i.test(value.trim());
        // Only suggest the purok text entered by the user, never invented names.
        const prefix = typingPurok ? value.trim() : (parts.length > 1 ? parts.slice(0, -1).join(',').trim() : '');
        const query = typingPurok ? '' : parts[parts.length - 1].trim().replace(/^(brgy\.?|barangay)\s+/i, '').toLowerCase();
        const options = barangays.filter(name => name.toLowerCase().includes(query)).map(name => {
            const option = document.createElement('option');
            option.value = (prefix ? prefix + ', ' : '') + name + ', Pio Duran, Albay';
            return option;
        });
        list.replaceChildren(...options);
    }
    input.addEventListener('input', update);
    input.addEventListener('focus', update);
    update();
})();
