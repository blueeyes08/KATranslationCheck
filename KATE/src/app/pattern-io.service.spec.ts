import { TestBed, inject } from '@angular/core/testing';

import { PatternIoService } from './pattern-io.service';

describe('PatternIoService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PatternIoService]
    });
  });

  it('should be created', inject([PatternIoService], (service: PatternIoService) => {
    expect(service).toBeTruthy();
  }));
});
