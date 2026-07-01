import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from documents.models import PolicyInformation
from django.db import transaction
import os
import logging
from decouple import config
from typing import Optional, Union

# S3 imports
import boto3
from botocore.exceptions import NoCredentialsError, ClientError, NoRegionError

class Command(BaseCommand):
    help = 'Update Market Source in PolicyInformation based on Policy Line Ref from Excel file.'

    def add_arguments(self, parser):
        parser.add_argument('--excel', type=str, default='May_cash_recon.xlsx', help='Excel file/key name')
        parser.add_argument('--log', type=str, default='market_source_update_log.txt', help='Log file name')

    @staticmethod
    def read_file_from_public_s3(
        bucket_name: str,
        file_key: str,
        region_name: Optional[str] = None,
        as_text: bool = False,
        encoding: str = 'utf-8',
        chunk_size: int = 1024 * 1024
    ) -> Union[bytes, str]:
        from botocore import UNSIGNED
        from botocore.config import Config
        s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        try:
            response = s3.get_object(Bucket=bucket_name, Key=file_key)
            body = response['Body']
            chunks = []
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b''.join(chunks)
            return data.decode(encoding) if as_text else data
        except s3.exceptions.NoSuchKey:
            logging.error(f"S3 file not found: {bucket_name}/{file_key}")
            raise FileNotFoundError(f"S3 file not found: {bucket_name}/{file_key}")
        except s3.exceptions.NoSuchBucket:
            logging.error(f"S3 bucket not found: {bucket_name}")
            raise FileNotFoundError(f"S3 bucket not found: {bucket_name}")
        except NoCredentialsError:
            logging.error("No AWS credentials found.")
            raise RuntimeError("No AWS credentials found.")
        except NoRegionError:
            logging.error("No AWS region specified.")
            raise RuntimeError("No AWS region specified.")
        except ClientError as e:
            logging.error(f"S3 ClientError: {e}")
            raise RuntimeError(f"S3 ClientError: {e}")
        except Exception as e:
            logging.error(f"Unexpected error reading S3 file: {e}")
            raise RuntimeError(f"Unexpected error reading S3 file: {e}")

    def handle(self, *args, **options):
        import datetime
        import io
        import time
        excel_file = options['excel']
        audit_file = 'market_source_update_audit.xlsx'

        # S3 params
        s3_bucket = config("DOCUMENTS_UPLOAD_BUCKET")
        s3_key = excel_file
        s3_region = os.environ.get('AWS_S3_REGION_NAME')

        start_time = time.time()
        try:
            # load Excel
            if s3_bucket and s3_key:
                self.stdout.write(self.style.NOTICE(f'Reading Excel from S3: {s3_bucket}/{s3_key}'))
                content = self.read_file_from_public_s3(s3_bucket, s3_key, s3_region, as_text=False)
                df = pd.read_excel(io.BytesIO(content), dtype=str)

            # common validation & cleanup
            required = ['Policy Line Ref', 'Market Source']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise CommandError(f"Missing columns: {missing}")

            df = df.dropna(subset=['Policy Line Ref'])
            df['Policy Line Ref'] = df['Policy Line Ref'].astype(str).str.strip()
            df['Market Source'] = df['Market Source'].astype(str).str.strip()
            df = df[df['Policy Line Ref'] != '']

            if df.empty:
                raise CommandError('No valid rows in Excel')

            # remove duplicate policy refs upfront
            df = df.drop_duplicates(subset=['Policy Line Ref'])
            self.stdout.write(self.style.SUCCESS(f'Processing {len(df)} unique Policy Line Refs'))

            # Prepare audit log list
            audit_rows = []
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for _, row in df.iterrows():
                ref = row['Policy Line Ref']
                src = row['Market Source']
                error = ''
                updated_count = 0
                try:
                    policies = list(PolicyInformation.objects.filter(Policy_Line_Ref=ref))
                    if not policies:
                        self.stdout.write(self.style.WARNING(f'No records for {ref}'))
                        error = 'No records found'
                    else:
                        for p in policies:
                            p.market_source = src
                        PolicyInformation.objects.bulk_update(policies, ['market_source'])
                        updated_count = len(policies)
                        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} for {ref} with market source : {src}'))
                        logging.info(f'Updated {ref} -> {src}')
                except Exception as e:
                    error = str(e)
                    self.stdout.write(self.style.ERROR(f'Error {ref}: {e}'))
                    logging.error(f'Error updating {ref}: {e}')
                audit_rows.append({
                    'policy line ref': ref,
                    'records to update': updated_count,
                    'market source': src,
                    'updated at': now_str,
                    'error (if any)': error
                })

            # Write audit log to Excel
            audit_df = pd.DataFrame(audit_rows, columns=[
                'policy line ref', 'records to update', 'market source', 'updated at', 'error (if any)'
            ])
            audit_df.to_excel(audit_file, index=False)
            self.stdout.write(self.style.SUCCESS(f'Audit log written to {audit_file}'))

            # Show summary
            stats = {
                'total': len(df),
                'updated_policies': sum(1 for r in audit_rows if r['records to update'] > 0),
                'updated_records': sum(r['records to update'] for r in audit_rows),
                'not_found': sum(1 for r in audit_rows if r['error (if any)'] == 'No records found'),
                'errors': sum(1 for r in audit_rows if r['error (if any)'] and r['error (if any)'] != 'No records found')
            }
            self._display_results(stats)

            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f'Time taken: {elapsed:.2f} seconds'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Command failed: {e}'))
            raise CommandError(f'Command failed: {e}')

    def _read_and_validate_excel(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            raise CommandError(f"Excel not found: {path}")
        try:
            df = pd.read_excel(path, dtype=str)
        except Exception as e:
            raise CommandError(f"Error reading Excel: {e}")
        return df

    # _process_updates is now inlined in handle and not used

    def _display_results(self, s: dict):
        self.stdout.write(self.style.SUCCESS('\nUPDATE RESULTS:'))
        self.stdout.write(f"Total refs: {s['total']}")
        self.stdout.write(f"Policies updated: {s['updated_policies']}")
        self.stdout.write(f"Records updated: {s['updated_records']}")
        self.stdout.write(f"Not found: {s['not_found']}")
        self.stdout.write(f"Errors: {s['errors']}")
