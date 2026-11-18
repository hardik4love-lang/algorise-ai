/**
 * Algorise PeopleOS - Real-Time Textile Stock & Inventory Engine
 * Designed for Process House HRMS (Dyeing, Printing, Folding, Dispatch)
 */

const AlgoriseStock = (function() {
  const STORAGE_KEY_ITEMS = 'algorise_stock_items';
  const STORAGE_KEY_INWARD = 'algorise_stock_inward';
  const STORAGE_KEY_OUTWARD = 'algorise_stock_outward';

  const INITIAL_ITEMS = [
    { id: 'STK001', code: 'GREY-SIKKA-60', name: 'Grey Sikka Shirting (Weaver Lot 42)', category: 'Grey Fabric', unit: 'Meters', qty: 52000, minQty: 20000, rate: 40.00, location: 'Godown 1 (Rack A-12)' },
    { id: 'STK002', code: 'GREY-RAYON-14KG', name: '14kg Liva Fluid Rayon Grey', category: 'Grey Fabric', unit: 'Meters', qty: 35000, minQty: 15000, rate: 45.00, location: 'Godown 1 (Rack B-04)' },
    { id: 'STK003', code: 'GREY-COTTON-CAMB', name: '60x60 Cambric Pure Cotton Grey', category: 'Grey Fabric', unit: 'Meters', qty: 34000, minQty: 10000, rate: 55.00, location: 'Godown 2 (Rack C-01)' },
    { id: 'STK004', code: 'DYE-REACTIVE-BLUE', name: 'Reactive Blue RGB 133% (Dyeing Color)', category: 'Dyeing Chemical', unit: 'Kg', qty: 140, minQty: 200, rate: 900.00, location: 'Chemical Store (Bin 4)' },
    { id: 'STK005', code: 'CHEM-CAUSTIC-FLK', name: 'Caustic Soda Flakes Rayon Grade', category: 'Auxiliary Chemical', unit: 'Kg', qty: 1800, minQty: 1000, rate: 50.00, location: 'Chemical Yard (Bags)' },
    { id: 'STK006', code: 'CHEM-PEROXIDE-50', name: 'Hydrogen Peroxide 50% (Bleaching Agent)', category: 'Auxiliary Chemical', unit: 'Carboys', qty: 25, minQty: 30, rate: 2500.00, location: 'Acid Yard' },
    { id: 'STK007', code: 'FIN-SIKKA-DYED', name: 'Dyed Sikka Navy Blue (Grade A Finished)', category: 'Finished Goods', unit: 'Meters', qty: 24000, minQty: 5000, rate: 70.00, location: 'Folding Dept Rack 1' },
    { id: 'STK008', code: 'FIN-RAYON-PRINT', name: 'Screen Printed Rayon Floral (Grade A)', category: 'Finished Goods', unit: 'Meters', qty: 20500, minQty: 5000, rate: 80.00, location: 'Folding Dept Rack 3' },
    { id: 'STK009', code: 'FIN-CAMBRIC-WHT', name: 'Optical White Finished Cambric', category: 'Finished Goods', unit: 'Meters', qty: 27000, minQty: 6000, rate: 70.00, location: 'Folding Dept Rack 2' },
    { id: 'STK010', code: 'FOLD-PACK-ROLLS', name: 'Inspection Passed Fabric Rolls (Packed)', category: 'Dispatch Ready', unit: 'Rolls', qty: 350, minQty: 50, rate: 11142.00, location: 'Dispatch Bay 1' }
  ];

  const INITIAL_INWARD = [
    { id: 'GRN-2026-1042', date: '28 Oct 2026', party: 'R.K. Synthetics (Surat)', category: 'Grey Fabric', item: 'Grey Sikka Shirting', takas: 45, qty: 12500, unit: 'Meters', rate: 40.00, total: 500000.00, vehicle: 'GJ-05-BX-4122', receivedBy: 'Nurzan Kumari' },
    { id: 'GRN-2026-1041', date: '27 Oct 2026', party: 'Jay Ambe Weaving Mills', category: 'Grey Fabric', item: '14kg Liva Fluid Rayon Grey', takas: 38, qty: 10400, unit: 'Meters', rate: 45.00, total: 468000.00, vehicle: 'GJ-19-V-8819', receivedBy: 'Nurzan Kumari' },
    { id: 'GRN-2026-1040', date: '25 Oct 2026', party: 'Atul Colors & Chemicals Ltd', category: 'Dyeing Chemical', item: 'Reactive Blue RGB 133%', takas: 10, qty: 250, unit: 'Kg', rate: 900.00, total: 225000.00, vehicle: 'GJ-16-Z-1002', receivedBy: 'Dheeraj Kumar Singh' },
    { id: 'GRN-2026-1039', date: '22 Oct 2026', party: 'Gujarat Alkalies & Chem (GACL)', category: 'Auxiliary Chemical', item: 'Caustic Soda Flakes', takas: 40, qty: 2000, unit: 'Kg', rate: 50.00, total: 100000.00, vehicle: 'GJ-06-AX-9911', receivedBy: 'Dheeraj Kumar Singh' }
  ];

  const INITIAL_OUTWARD = [
    { id: 'GP-2026-0891', date: '28 Oct 2026', buyer: 'Mahalaxmi Textile Traders (Ring Road, Surat)', item: 'Dyed Sikka Navy Blue', lots: 22, qty: 8500, unit: 'Meters', vehicle: 'GJ-05-AT-7811', driver: 'Mukesh Bhai (9825100001)', dest: 'Radha Krishna Market, Surat', status: 'Delivered' },
    { id: 'GP-2026-0890', date: '26 Oct 2026', buyer: 'Shree Kuberji Fashions (Surat)', item: 'Screen Printed Rayon Floral', lots: 18, qty: 7200, unit: 'Meters', vehicle: 'GJ-05-BX-1120', driver: 'Raju Patel (9825100002)', dest: 'Millennium Market-2, Surat', status: 'Delivered' },
    { id: 'GP-2026-0889', date: '24 Oct 2026', buyer: 'Vimal Cotton Agency (Ahmedabad)', item: 'Optical White Finished Cambric', lots: 25, qty: 10000, unit: 'Meters', vehicle: 'GJ-01-CZ-3344', driver: 'Dinesh Yadav (9825100003)', dest: 'Maskati Market, Ahmedabad', status: 'Delivered' }
  ];

  function getItems() {
    try {
      const data = localStorage.getItem(STORAGE_KEY_ITEMS);
      if (data) return JSON.parse(data);
    } catch(e) {}
    localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(INITIAL_ITEMS));
    return INITIAL_ITEMS;
  }

  function saveItems(items) {
    localStorage.setItem(STORAGE_KEY_ITEMS, JSON.stringify(items));
  }

  function getInward() {
    try {
      const data = localStorage.getItem(STORAGE_KEY_INWARD);
      if (data) return JSON.parse(data);
    } catch(e) {}
    localStorage.setItem(STORAGE_KEY_INWARD, JSON.stringify(INITIAL_INWARD));
    return INITIAL_INWARD;
  }

  function addInward(record) {
    const list = getInward();
    list.unshift(record);
    localStorage.setItem(STORAGE_KEY_INWARD, JSON.stringify(list));

    // Also update current item quantity
    const items = getItems();
    const item = items.find(i => i.name.toLowerCase().includes(record.item.toLowerCase()) || i.code.toLowerCase() === record.item.toLowerCase());
    if (item) {
      item.qty += Number(record.qty);
      saveItems(items);
    }
    return list;
  }

  function getOutward() {
    try {
      const data = localStorage.getItem(STORAGE_KEY_OUTWARD);
      if (data) return JSON.parse(data);
    } catch(e) {}
    localStorage.setItem(STORAGE_KEY_OUTWARD, JSON.stringify(INITIAL_OUTWARD));
    return INITIAL_OUTWARD;
  }

  function addOutward(record) {
    const list = getOutward();
    list.unshift(record);
    localStorage.setItem(STORAGE_KEY_OUTWARD, JSON.stringify(list));

    // Deduct from stock
    const items = getItems();
    const item = items.find(i => i.name.toLowerCase().includes(record.item.toLowerCase()) || i.code.toLowerCase() === record.item.toLowerCase());
    if (item) {
      item.qty = Math.max(0, item.qty - Number(record.qty));
      saveItems(items);
    }
    return list;
  }

  function getSummary() {
    const items = getItems();
    let totalGreyMeters = 0;
    let totalChemicalKg = 0;
    let totalFinishedMeters = 0;
    let totalValuation = 0;
    let lowStockCount = 0;

    items.forEach(i => {
      const val = i.qty * i.rate;
      totalValuation += val;

      if (i.category === 'Grey Fabric') totalGreyMeters += i.qty;
      else if (i.category.includes('Chemical')) totalChemicalKg += i.qty;
      else if (i.category === 'Finished Goods') totalFinishedMeters += i.qty;

      if (i.qty <= i.minQty) lowStockCount++;
    });

    return {
      totalGreyMeters,
      totalChemicalKg,
      totalFinishedMeters,
      totalValuation,
      lowStockCount,
      totalSKUs: items.length
    };
  }

  return {
    getItems,
    saveItems,
    getInward,
    addInward,
    getOutward,
    addOutward,
    getSummary
  };
})();

// Auto-initialize on window
if (typeof window !== 'undefined') {
  window.AlgoriseStock = AlgoriseStock;
}
