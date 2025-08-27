import useSWR from 'swr';

const fetcher = (url) => fetch(url, { credentials: 'include' }).then(r => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
});

export default function useHomeTop3() {
  return useSWR('/predictions/api/home-top3/', fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 30_000,
  });
}
