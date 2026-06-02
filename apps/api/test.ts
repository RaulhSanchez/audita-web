const run = async () => {
  try {
    const response = await fetch('http://localhost:3002/api/audits', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://zero2dev.es/' }),
    });
    console.log(await response.json());
  } catch (e) {
    console.error(e);
  }
};
run();
