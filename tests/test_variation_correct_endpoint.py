"""
Test the correct NCBI Variation API endpoint for VCF rsID annotation.
Based on https://api.ncbi.nlm.nih.gov/variation/v0/#/VCF/post_vcf_file_set_rsids
"""
import requests

# VCF content with 3 chr16 positions
VCF_CONTENT = """##fileformat=VCFv4.2
##source=test
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
16	55758285	.	A	G	.	.	.
16	55758328	.	C	T	.	.	.
16	55758525	.	G	A	.	.	.
"""

def test_variation_api():
    url = "https://api.ncbi.nlm.nih.gov/variation/v0/vcf/file/set_rsids"
    
    params = {
        "assembly": "GCF_000001405.40"  # GRCh38
    }
    
    headers = {
        "accept": "text/plain; charset=utf-8",
        "Content-Type": "text/plain; charset=utf-8"
    }
    
    print("Testing NCBI Variation API VCF rsID annotation endpoint...")
    print(f"URL: {url}")
    print(f"Assembly: {params['assembly']}")
    print("\nSending VCF with 3 variants on chr16...")
    
    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
            data=VCF_CONTENT,
            timeout=30
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            print("\n✓ SUCCESS! Annotated VCF:")
            print("="*60)
            print(response.text)
            print("="*60)
            
            # Count rsIDs found
            lines = response.text.split('\n')
            annotated = [l for l in lines if not l.startswith('#') and l.strip() and '\trs' in l]
            print(f"\nAnnotated variants: {len(annotated)}/{3}")
            
        elif response.status_code == 500:
            print("\n✗ 500 Internal Server Error - NCBI backend is down")
            try:
                print("Response:", response.json())
            except:
                print("Response:", response.text[:500])
                
        else:
            print(f"\n✗ Failed with status {response.status_code}")
            try:
                print("Response:", response.json())
            except:
                print("Response:", response.text[:500])
                
    except Exception as e:
        print(f"\n✗ Request failed: {e}")

if __name__ == "__main__":
    test_variation_api()
