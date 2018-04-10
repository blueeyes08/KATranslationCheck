import {HttpClient, HttpParams} from '@angular/common/http';
import {Injectable} from '@angular/core';
import { Pattern } from './patterns';

import 'rxjs/add/operator/map';

@Injectable()
export class PatternIoService {

  constructor(private http: HttpClient) { }

  patterns(): Promise<Pattern[]> {
    return this.http.get<Pattern[]>('/api/patterns').toPromise();
  }

  texttag(): Promise<Pattern[]> {
    return this.http.get<Pattern[]>('/api/texttags').toPromise();
  }

  savePattern(pattern: Pattern, type= 'texttag'): Promise<any> {
    return this.http.post(`/api/${type}`, pattern).toPromise();
  }
}
